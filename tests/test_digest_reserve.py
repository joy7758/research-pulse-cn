from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    PaperType,
    SignalSource,
    SubscriptionFrequency,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Digest User",
            "email": email,
            "field": "Materials",
            "interests": ["signals"],
            "watched_topics": ["citations"],
            "watched_venues": ["JOM"],
            "reminder_preferences": {"timezone": "UTC"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_paper(client, headers, *, user_id: str, title: str) -> dict:
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": PaperType.PUBLISHED.value,
            "stage": "published",
            "venue": "JOM",
            "identifiers": {},
            "source_links": [f"https://example.local/{title.lower().replace(' ', '-')}"],
            "last_touch_at": (utcnow() - timedelta(days=14)).isoformat(),
            "next_action": "Review the latest signal delta",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_signal_pair(client, headers, *, paper_id: str, latest_delta: int = 4) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (10 + latest_delta, 60 + latest_delta, 90 + latest_delta, newer),
    ):
        response = client.post(
            f"/papers/{paper_id}/signal-snapshots",
            headers=headers,
            json={
                "source": SignalSource.GOOGLE_SCHOLAR.value,
                "citation_count": citation_count,
                "download_count": download_count,
                "read_count": read_count,
                "inclusion_status": "indexed",
                "fetched_at": fetched_at.isoformat(),
            },
        )
        assert response.status_code == 201


def create_policy(client, headers, *, user_id: str) -> None:
    response = client.post(
        "/subscription-policies",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": "webhook",
            "enabled": True,
            "frequency": SubscriptionFrequency.EVENT.value,
            "frequency_cap": 3,
            "endpoint": "https://hooks.example.local/research-pulse",
            "policy": {"digest": True},
        },
    )
    assert response.status_code == 201


def create_device(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/client-devices",
        headers=headers,
        json={
            "user_id": user_id,
            "client_type": "desktop",
            "display_name": "Digest Desktop",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_digest_ready_user(client, headers, *, email: str) -> tuple[dict, dict]:
    user = create_user(client, headers, email=email)
    paper = create_paper(client, headers, user_id=user["id"], title="Digest Ranking Paper")
    add_signal_pair(client, headers, paper_id=paper["id"])
    create_policy(client, headers, user_id=user["id"])
    run_response = client.post(f"/pulse/run/{user['id']}", headers=headers)
    assert run_response.status_code == 200
    return user, run_response.json()


def test_operator_can_create_and_update_wechat_bindings(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="binding-operator@example.com")

    created = client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "openid-001",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Primary OA",
            "metadata": {"note": "manual bind"},
        },
    )
    binding_id = created.json()["id"]
    updated = client.patch(
        f"/admin/wechat-bindings/{binding_id}",
        headers=operator_headers,
        json={
            "digest_enabled": False,
            "display_label": "Primary OA Updated",
            "metadata": {"note": "updated"},
        },
    )

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["digest_enabled"] is False
    assert updated.json()["display_label"] == "Primary OA Updated"


def test_viewer_cannot_manage_wechat_bindings(client, operator_headers, viewer_headers) -> None:
    user = create_user(client, operator_headers, email="binding-viewer@example.com")

    response = client.post(
        "/admin/wechat-bindings",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "openid-002",
        },
    )

    assert response.status_code == 403


def test_manual_digest_build_is_idempotent_per_user_and_date(client, operator_headers) -> None:
    user, run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-idempotent@example.com",
    )
    issues = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    assert issues.status_code == 200
    issue = issues.json()[0]

    first_build = client.post(
        f"/admin/digest-issues/build/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": issue["issue_date"],
            "source_pulse_job_id": run_payload["job"]["id"],
        },
    )
    second_build = client.post(
        f"/admin/digest-issues/build/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": issue["issue_date"],
            "source_pulse_job_id": run_payload["job"]["id"],
        },
    )
    issues_after = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"], "issue_date": issue["issue_date"]},
    )

    assert first_build.status_code == 200
    assert second_build.status_code == 200
    assert first_build.json()["issue"]["id"] == issue["id"]
    assert second_build.json()["issue"]["id"] == issue["id"]
    assert len(issues_after.json()) == 1


def test_daily_pulse_completion_auto_upserts_digest_issue(client, operator_headers) -> None:
    user, run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-auto@example.com",
    )

    issues = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )

    assert issues.status_code == 200
    assert len(issues.json()) == 1
    assert issues.json()[0]["source_pulse_job_id"] == run_payload["job"]["id"]
    assert issues.json()[0]["status"] == "ready"


def test_digest_items_preserve_stable_order_from_selected_cards(client, operator_headers) -> None:
    user, run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-order@example.com",
    )
    issues = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    digest_issue_id = issues.json()[0]["id"]

    detail = client.get(f"/admin/digest-issues/{digest_issue_id}", headers=operator_headers)

    assert detail.status_code == 200
    assert [item["pulse_card_id"] for item in detail.json()["items"]] == [
        card["id"] for card in run_payload["cards"]
    ]


def test_prepare_publication_only_uses_eligible_official_account_bindings(
    client,
    operator_headers,
) -> None:
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-prepare@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]

    binding_payloads = [
        {
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "eligible-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
        {
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "not-subscribed",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": False,
            "digest_enabled": True,
        },
        {
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "revoked-openid",
            "bind_state": WeChatBindingState.REVOKED.value,
            "subscribed": True,
            "digest_enabled": True,
        },
        {
            "channel_type": WeChatBindingChannelType.MINI_PROGRAM.value,
            "app_id": "wx-mini-app",
            "openid": "mini-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    ]
    for payload in binding_payloads:
        response = client.post(
            "/admin/wechat-bindings",
            headers=operator_headers,
            json={"user_id": user["id"], **payload},
        )
        assert response.status_code == 201

    prepared = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    )

    assert prepared.status_code == 200
    assert len(prepared.json()["publication_jobs"]) == 1
    job = prepared.json()["publication_jobs"][0]
    assert job["status"] == "previewed"
    assert job["publish_target"] == "official_account"
    assert job["provider_name"] == "stub"
    assert job["external_message_id"] is None
    assert job["payload"]["binding"]["openid"] == "eligible-openid"


def test_digest_metrics_appear_on_ops_metrics(client, operator_headers) -> None:
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-metrics@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "metrics-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    )

    metrics = client.get("/ops/metrics", headers=operator_headers)

    assert metrics.status_code == 200
    assert "digest_issues_built_total" in metrics.text
    assert "digest_publication_jobs_prepared_total" in metrics.text
    assert "digest_publication_jobs_failed_total" in metrics.text


def test_digest_issue_sync_event_is_emitted(client, operator_headers) -> None:
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-sync@example.com",
    )
    created_device = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created_device['plain_text_token']}"}

    feed = client.get("/sync/feed", headers=device_headers)

    assert feed.status_code == 200
    assert any(event["entity_type"] == "pulse_digest_issue" for event in feed.json()["events"])


def test_device_token_cannot_access_digest_admin_routes(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="digest-device-block@example.com")
    created_device = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created_device['plain_text_token']}"}

    response = client.get("/admin/digest-issues", headers=device_headers)

    assert response.status_code == 401
