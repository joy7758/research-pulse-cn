from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    MiniReadGrantType,
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
            "name": "Mini User",
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


def create_paper(
    client,
    headers,
    *,
    user_id: str,
    title: str,
    paper_type: str = PaperType.PUBLISHED.value,
) -> dict:
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": paper_type,
            "stage": paper_type,
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


def add_signal_pair(client, headers, *, paper_id: str) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (14, 68, 111, newer),
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


def create_digest_ready_user(client, headers, *, email: str) -> tuple[dict, dict, dict]:
    user = create_user(client, headers, email=email)
    paper = create_paper(client, headers, user_id=user["id"], title="Mini Digest Paper")
    add_signal_pair(client, headers, paper_id=paper["id"])
    create_policy(client, headers, user_id=user["id"])
    run_response = client.post(f"/pulse/run/{user['id']}", headers=headers)
    assert run_response.status_code == 200
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=headers,
        params={"user_id": user["id"]},
    ).json()[0]
    return user, paper, digest_issue


def create_mini_grant(
    client,
    headers,
    *,
    user_id: str,
    grant_type: str = MiniReadGrantType.PREVIEW.value,
    binding_id: str | None = None,
    digest_issue_id: str | None = None,
    expires_at: str | None = None,
    scope: dict | None = None,
) -> dict:
    payload = {"user_id": user_id, "grant_type": grant_type}
    if binding_id is not None:
        payload["binding_id"] = binding_id
    if digest_issue_id is not None:
        payload["digest_issue_id"] = digest_issue_id
    if expires_at is not None:
        payload["expires_at"] = expires_at
    if scope is not None:
        payload["scope"] = scope
    response = client.post("/admin/mini-read-grants", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def test_operator_can_create_mini_read_grant_and_receive_plaintext_token_once(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-grant-create@example.com")

    created = create_mini_grant(client, operator_headers, user_id=user["id"])
    listed = client.get("/admin/mini-read-grants", headers=operator_headers)

    assert created["grant"]["user_id"] == user["id"]
    assert created["plain_text_token"]
    assert created["preview_landing_path"] == "/mini/today"
    assert "plain_text_token" not in listed.json()[0]


def test_viewer_cannot_create_mini_read_grant(client, operator_headers, viewer_headers) -> None:
    user = create_user(client, operator_headers, email="mini-grant-viewer@example.com")

    response = client.post(
        "/admin/mini-read-grants",
        headers=viewer_headers,
        json={"user_id": user["id"], "grant_type": MiniReadGrantType.PREVIEW.value},
    )

    assert response.status_code == 403


def test_mini_grant_token_can_access_mini_routes_but_not_other_boundaries(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-access@example.com")
    created = create_mini_grant(client, operator_headers, user_id=user["id"])
    mini_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    bootstrap = client.get("/mini/bootstrap", headers=mini_headers)
    admin_route = client.get("/admin/admin-accounts", headers=mini_headers)
    ops_route = client.get("/ops/metrics", headers=mini_headers)
    sync_route = client.get("/sync/me", headers=mini_headers)
    business_route = client.get("/users", headers=mini_headers)

    assert bootstrap.status_code == 200
    assert admin_route.status_code == 401
    assert ops_route.status_code == 401
    assert sync_route.status_code == 401
    assert business_route.status_code == 401


def test_revoked_mini_grant_is_rejected(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="mini-revoke@example.com")
    created = create_mini_grant(client, operator_headers, user_id=user["id"])
    mini_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    revoke = client.post(
        f"/admin/mini-read-grants/{created['grant']['id']}/revoke",
        headers=operator_headers,
    )
    bootstrap = client.get("/mini/bootstrap", headers=mini_headers)

    assert revoke.status_code == 200
    assert bootstrap.status_code == 401


def test_expired_mini_grant_is_rejected(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="mini-expired@example.com")
    created = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        expires_at=(utcnow() - timedelta(minutes=1)).isoformat(),
    )

    response = client.get(
        "/mini/bootstrap",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 401


def test_mini_bootstrap_returns_stable_grant_context(client, operator_headers) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-bootstrap@example.com",
    )
    binding = client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.MINI_PROGRAM.value,
            "app_id": "wx-mini-app",
            "openid": "mini-openid-001",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Mini Preview Binding",
        },
    ).json()
    created = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        grant_type=MiniReadGrantType.DIGEST_LANDING.value,
        binding_id=binding["id"],
        digest_issue_id=digest_issue["id"],
    )

    bootstrap = client.get(
        "/mini/bootstrap",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload["default_landing_path"] == f"/mini/digest-issues/{digest_issue['id']}"
    assert (
        payload["grant"]["binding"]["channel_type"] == WeChatBindingChannelType.MINI_PROGRAM.value
    )
    assert payload["grant"]["digest_issue_id"] == digest_issue["id"]
    assert "/mini/digest-issues/{digest_issue_id}" in payload["available_routes"]


def test_mini_today_returns_empty_state_when_no_digest_exists(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="mini-empty@example.com")
    created = create_mini_grant(client, operator_headers, user_id=user["id"])

    response = client.get(
        "/mini/today",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "empty"
    assert response.json()["digest_issue"] is None


def test_mini_digest_issue_preserves_sort_order(client, operator_headers) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-digest-order@example.com",
    )
    created = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        grant_type=MiniReadGrantType.DIGEST_LANDING.value,
        digest_issue_id=digest_issue["id"],
    )

    response = client.get(
        f"/mini/digest-issues/{digest_issue['id']}",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    sort_orders = [item["sort_order"] for item in response.json()["items"]]
    assert sort_orders == sorted(sort_orders)


def test_mini_digest_issue_exposes_sectioned_digest_payload_compatibly(
    client,
    operator_headers,
) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-digest-sections@example.com",
    )
    created = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        grant_type=MiniReadGrantType.DIGEST_LANDING.value,
        digest_issue_id=digest_issue["id"],
    )

    response = client.get(
        f"/mini/digest-issues/{digest_issue['id']}",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["section_order"] == [
        "today_focus",
        "yesterday_recap",
        "signal_updates",
        "related_papers",
        "other_updates",
    ]
    assert "publication_preview" in response.json()


def test_mini_paper_detail_exposes_derived_progress_percentage_mapping(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-progress@example.com")
    created = create_mini_grant(client, operator_headers, user_id=user["id"])
    mini_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    mapping = {
        PaperType.PUBLISHED.value: 100,
        PaperType.REVISION.value: 80,
        PaperType.UNDER_REVIEW.value: 65,
        PaperType.IN_PREP.value: 35,
        PaperType.PAUSED.value: 0,
    }

    for paper_type, expected_progress in mapping.items():
        paper = create_paper(
            client,
            operator_headers,
            user_id=user["id"],
            title=f"Mini {paper_type}",
            paper_type=paper_type,
        )
        response = client.get(f"/mini/papers/{paper['id']}", headers=mini_headers)
        assert response.status_code == 200
        assert response.json()["progress_percentage"] == expected_progress


def test_mini_metrics_are_exposed_on_ops_metrics(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="mini-metrics@example.com")
    created = create_mini_grant(client, operator_headers, user_id=user["id"])
    mini_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    bootstrap = client.get("/mini/bootstrap", headers=mini_headers)
    revoke = client.post(
        f"/admin/mini-read-grants/{created['grant']['id']}/revoke",
        headers=operator_headers,
    )
    metrics = client.get("/ops/metrics", headers=operator_headers)

    assert bootstrap.status_code == 200
    assert revoke.status_code == 200
    assert metrics.status_code == 200
    body = metrics.text
    assert "mini_read_grants_issued_total" in body
    assert "mini_read_grants_revoked_total" in body
    assert "mini_read_requests_total" in body
