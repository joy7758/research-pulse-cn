from datetime import timedelta
from uuid import UUID

from research_pulse_cn.db.models import PulseDigestIssue, utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
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


def ensure_official_account_policy(
    client,
    headers,
    *,
    user_id: str,
    enabled: bool = True,
    quiet_hours: dict | None = None,
    policy: dict | None = None,
) -> dict:
    response = client.get(
        "/subscription-policies",
        headers=headers,
        params={"user_id": user_id},
    )
    assert response.status_code == 200
    for existing in response.json():
        if existing["channel"] != ChannelType.OFFICIAL_ACCOUNT.value:
            continue
        updated = client.put(
            f"/subscription-policies/{existing['id']}",
            headers=headers,
            json={
                "enabled": enabled,
                "quiet_hours": quiet_hours if quiet_hours is not None else existing["quiet_hours"],
                "policy": policy if policy is not None else existing["policy"],
            },
        )
        assert updated.status_code == 200
        return updated.json()
    created = client.post(
        "/subscription-policies",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": ChannelType.OFFICIAL_ACCOUNT.value,
            "enabled": enabled,
            "frequency": SubscriptionFrequency.DAILY.value,
            "frequency_cap": 3,
            "endpoint": None,
            "quiet_hours": quiet_hours,
            "policy": policy or {"timezone": "UTC"},
        },
    )
    assert created.status_code == 201
    return created.json()


def create_official_account_binding(client, headers, *, user_id: str, openid: str) -> dict:
    response = client.post(
        "/admin/wechat-bindings",
        headers=headers,
        json={
            "user_id": user_id,
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": openid,
            "unionid": "mini-should-not-see-unionid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Official Account Binding",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_self_service_grant(
    client,
    headers,
    *,
    user_id: str,
    binding_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "user_id": user_id,
        "channel": ChannelType.OFFICIAL_ACCOUNT.value,
    }
    if binding_id is not None:
        payload["binding_id"] = binding_id
    response = client.post(
        "/admin/subscription-self-service-grants",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


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
    assert "/mini/subscription-reserve" in payload["available_routes"]
    assert payload["subscription_reserve_summary"]["self_service_reserve"]["supported"] is True
    assert (
        payload["subscription_reserve_summary"]["self_service_reserve"][
            "editable_via_current_mini_grant"
        ]
        is False
    )


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


def test_mini_today_returns_structured_sections_when_digest_payload_is_structured(
    client,
    operator_headers,
) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-today-structured@example.com",
    )
    created = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        grant_type=MiniReadGrantType.DIGEST_LANDING.value,
        digest_issue_id=digest_issue["id"],
    )

    response = client.get(
        "/mini/today",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()["digest_issue"]
    assert payload["is_structured"] is True
    assert payload["fallback_mode"] == "structured"
    assert payload["section_order"] == [
        "today_focus",
        "yesterday_recap",
        "signal_updates",
        "related_papers",
        "other_updates",
    ]
    assert payload["sections"]
    assert "quick_stats" in payload
    assert "publication_preview" in payload


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


def test_mini_today_falls_back_cleanly_on_legacy_highlight_only_digest(
    client,
    operator_headers,
    session,
) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-today-legacy@example.com",
    )
    issue_model = session.get(PulseDigestIssue, UUID(digest_issue["id"]))
    assert issue_model is not None
    structured_item = dict((issue_model.content_payload or {})["items"][0])
    issue_model.content_payload = {
        "highlights": [structured_item],
        "items": [structured_item],
    }
    session.commit()

    created = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        grant_type=MiniReadGrantType.DIGEST_LANDING.value,
        digest_issue_id=digest_issue["id"],
    )
    response = client.get(
        "/mini/today",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()["digest_issue"]
    assert payload["is_structured"] is False
    assert payload["fallback_mode"] == "highlights_only"
    assert payload["sections"]
    assert payload["sections"][0]["kind"] == "signal_updates"


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


def test_mini_digest_issue_handles_null_source_paper_in_structured_sections(
    client,
    operator_headers,
    session,
) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-digest-null-source-paper@example.com",
    )
    issue_model = session.get(PulseDigestIssue, UUID(digest_issue["id"]))
    assert issue_model is not None
    legacy_item = {
        "sort_order": 1,
        "pulse_card_id": str(issue_model.items[0].pulse_card_id),
        "card_type": "yesterday_summary",
        "source_paper_id": None,
        "title": "Yesterday summary for 2026-04-15",
        "summary": "Yesterday recorded 2 work activities.",
        "why_now": "This recap is still useful today.",
        "action_text": None,
        "deep_link": None,
    }
    issue_model.content_payload = {
        "section_order": [
            "today_focus",
            "yesterday_recap",
            "signal_updates",
            "related_papers",
            "other_updates",
        ],
        "sections": [
            {
                "kind": "yesterday_recap",
                "title": "Yesterday Recap",
                "item_count": 1,
                "items": [legacy_item],
            }
        ],
        "quick_stats": {
            "selected_card_count": 1,
            "related_paper_count": 0,
            "signal_update_count": 0,
            "touched_paper_count": 0,
        },
        "focus_card": None,
        "publication_preview": None,
        "highlights": [legacy_item],
        "items": [legacy_item],
    }
    session.commit()

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
    payload = response.json()
    assert payload["sections"][0]["kind"] == "yesterday_recap"
    assert payload["sections"][0]["items"][0]["source_paper_id"] is None
    assert payload["highlights"][0]["source_paper_id"] is None


def test_mini_subscription_reserve_returns_safe_binding_summary_and_authoritative_preview(
    client,
    operator_headers,
) -> None:
    user, _paper, digest_issue = create_digest_ready_user(
        client,
        operator_headers,
        email="mini-subscription-reserve@example.com",
    )
    ensure_official_account_policy(
        client,
        operator_headers,
        user_id=user["id"],
        policy={"timezone": "UTC", "minimum_selected_cards": 5},
    )
    create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="mini-subscription-openid",
    )
    created = create_mini_grant(client, operator_headers, user_id=user["id"])

    response = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["official_account_binding"]["channel_type"] == "official_account"
    assert "openid" not in payload["official_account_binding"]
    assert "unionid" not in payload["official_account_binding"]
    assert payload["subscription_settings"]["channel"] == "official_account"
    assert payload["delivery_control_preview"]["state"] == "ready"
    assert payload["delivery_control_preview"]["decision"] == "skipped"
    assert "insufficient_selected_cards" in payload["delivery_control_preview"]["reason_codes"]
    assert payload["latest_digest_issue"]["id"] == digest_issue["id"]
    assert payload["self_service_reserve"]["editable_via_current_mini_grant"] is False
    assert payload["self_service_entry"]["editable_via_current_mini_grant"] is False
    assert payload["self_service_entry"]["editor_contract_available"] is True
    assert payload["self_service_entry"]["editor_preview_available"] is True


def test_mini_subscription_reserve_returns_empty_preview_when_digest_context_absent(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-subscription-empty@example.com")
    ensure_official_account_policy(
        client,
        operator_headers,
        user_id=user["id"],
        policy={"timezone": "UTC", "skip_if_no_today_focus": True},
    )
    created = create_mini_grant(client, operator_headers, user_id=user["id"])

    response = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["delivery_control_preview"]["state"] == "empty"
    assert payload["delivery_control_preview"]["decision"] is None
    assert payload["latest_digest_issue"] is None
    assert payload["self_service_entry"]["separate_self_service_grant_required"] is True


def test_mini_grant_cannot_access_self_service_routes_and_self_service_grant_cannot_access_mini(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-vs-self-service@example.com")
    mini_grant = create_mini_grant(client, operator_headers, user_id=user["id"])
    self_service_grant = create_self_service_grant(
        client,
        operator_headers,
        user_id=user["id"],
    )

    mini_on_self_service = client.get(
        "/subscription-self-service/bootstrap",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )
    self_service_on_mini = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {self_service_grant['plain_text_token']}"},
    )
    mini_patch_self_service = client.patch(
        "/subscription-self-service/settings",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
        json={"enabled": False},
    )
    mini_editor_bootstrap = client.get(
        "/subscription-self-service/editor-bootstrap",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )
    mini_editor_preview = client.post(
        "/subscription-self-service/settings/preview",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
        json={"enabled": False},
    )

    assert mini_on_self_service.status_code == 401
    assert self_service_on_mini.status_code == 401
    assert mini_patch_self_service.status_code == 401
    assert mini_editor_bootstrap.status_code == 401
    assert mini_editor_preview.status_code == 401


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
