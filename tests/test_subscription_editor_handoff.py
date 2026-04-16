from datetime import timedelta

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    MiniReadGrantType,
    PaperType,
    SignalSource,
    SubscriptionFrequency,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def enable_handoff(monkeypatch, *, ttl_minutes: int = 15) -> None:
    monkeypatch.setenv("APP_SUBSCRIPTION_EDITOR_HANDOFF_ENABLED", "true")
    monkeypatch.setenv("APP_SUBSCRIPTION_EDITOR_HANDOFF_TTL_MINUTES", str(ttl_minutes))
    get_settings.cache_clear()


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Editor Handoff User",
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
            "last_touch_at": (utcnow() - timedelta(days=5)).isoformat(),
            "next_action": "Review the latest signal delta",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_signal_pair(client, headers, *, paper_id: str) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, read_count, fetched_at in (
        (10, 80, older),
        (14, 91, newer),
    ):
        response = client.post(
            f"/papers/{paper_id}/signal-snapshots",
            headers=headers,
            json={
                "source": SignalSource.GOOGLE_SCHOLAR.value,
                "citation_count": citation_count,
                "download_count": 50 + citation_count,
                "read_count": read_count,
                "inclusion_status": "indexed",
                "fetched_at": fetched_at.isoformat(),
            },
        )
        assert response.status_code == 201


def ensure_official_account_policy(
    client,
    headers,
    *,
    user_id: str,
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
                "enabled": True,
                "quiet_hours": existing["quiet_hours"],
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
            "enabled": True,
            "frequency": SubscriptionFrequency.DAILY.value,
            "frequency_cap": 3,
            "endpoint": None,
            "quiet_hours": None,
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
            "unionid": "hidden-unionid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "OA Binding",
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


def create_mini_grant(
    client,
    headers,
    *,
    user_id: str,
    binding_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "user_id": user_id,
        "grant_type": MiniReadGrantType.PREVIEW.value,
    }
    if binding_id is not None:
        payload["binding_id"] = binding_id
    response = client.post("/admin/mini-read-grants", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def create_digest_issue(client, headers, *, user_id: str) -> dict:
    paper = create_paper(client, headers, user_id=user_id, title="Editor Handoff Digest Paper")
    add_signal_pair(client, headers, paper_id=paper["id"])
    response = client.post(f"/pulse/run/{user_id}", headers=headers)
    assert response.status_code == 200
    issues = client.get("/admin/digest-issues", headers=headers, params={"user_id": user_id})
    assert issues.status_code == 200
    return issues.json()[0]


def setup_handoff_ready_user(client, headers, *, email: str) -> tuple[dict, dict, dict, dict]:
    user = create_user(client, headers, email=email)
    binding = create_official_account_binding(
        client,
        headers,
        user_id=user["id"],
        openid=f"openid-{email}",
    )
    ensure_official_account_policy(
        client,
        headers,
        user_id=user["id"],
        policy={"timezone": "UTC", "stale_days": 10},
    )
    self_service_grant = create_self_service_grant(
        client,
        headers,
        user_id=user["id"],
        binding_id=binding["id"],
    )
    mini_grant = create_mini_grant(
        client,
        headers,
        user_id=user["id"],
        binding_id=binding["id"],
    )
    return user, binding, self_service_grant, mini_grant


def test_mini_grant_can_create_handoff_grant_when_active_self_service_grant_exists(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_handoff(monkeypatch)
    _user, _binding, _self_service_grant, mini_grant = setup_handoff_ready_user(
        client,
        operator_headers,
        email="mini-handoff-create@example.com",
    )
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}

    created = client.post("/mini/subscription-reserve/editor-handoff", headers=mini_headers)
    status = client.get("/mini/subscription-reserve/editor-handoff-status", headers=mini_headers)

    assert created.status_code == 201
    payload = created.json()
    assert payload["handoff_grant"]["mini_grant_id"] == mini_grant["grant"]["id"]
    assert payload["plain_text_token"]
    assert "/subscription-editor/bootstrap" in payload["supported_editor_endpoints"]
    assert status.status_code == 200
    assert status.json()["handoff_grant"]["id"] == payload["handoff_grant"]["id"]


def test_mini_grant_cannot_create_handoff_when_disabled_or_missing_self_service_grant(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    user = create_user(client, operator_headers, email="mini-handoff-disabled@example.com")
    binding = create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="mini-handoff-disabled-openid",
    )
    mini_grant = create_mini_grant(
        client,
        operator_headers,
        user_id=user["id"],
        binding_id=binding["id"],
    )
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}

    disabled = client.post("/mini/subscription-reserve/editor-handoff", headers=mini_headers)
    assert disabled.status_code == 422

    enable_handoff(monkeypatch)
    missing_grant = client.post("/mini/subscription-reserve/editor-handoff", headers=mini_headers)
    assert missing_grant.status_code == 422


def test_handoff_grant_can_access_editor_bootstrap_contract_preview_and_patch(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_handoff(monkeypatch)
    user, _binding, self_service_grant, mini_grant = setup_handoff_ready_user(
        client,
        operator_headers,
        email="mini-handoff-editor@example.com",
    )
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}
    created = client.post("/mini/subscription-reserve/editor-handoff", headers=mini_headers)
    handoff_headers = {"Authorization": f"Bearer {created.json()['plain_text_token']}"}

    bootstrap = client.get("/subscription-editor/bootstrap", headers=handoff_headers)
    contract = client.get("/subscription-editor/contract", headers=handoff_headers)
    preview = client.post(
        "/subscription-editor/settings/preview",
        headers=handoff_headers,
        json={
            "timezone": "Asia/Shanghai",
            "allowed_weekdays": [4, 2, 2, 0],
            "minimum_selected_cards": 2,
            "skip_if_no_today_focus": True,
        },
    )
    saved = client.patch(
        "/subscription-editor/settings?include_preview=true",
        headers=handoff_headers,
        json={
            "timezone": "Asia/Shanghai",
            "minimum_selected_cards": 2,
        },
    )
    admin_policy = client.get(
        "/subscription-policies",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    self_service_headers = {"Authorization": f"Bearer {self_service_grant['plain_text_token']}"}
    self_service_bootstrap = client.get(
        "/subscription-self-service/editor-bootstrap",
        headers=self_service_headers,
    )

    assert bootstrap.status_code == 200
    assert (
        bootstrap.json()["handoff_grant"]["self_service_grant_id"]
        == self_service_grant["grant"]["id"]
    )
    assert contract.status_code == 200
    assert contract.json()["contract_version"] == "v1"
    assert preview.status_code == 200
    assert preview.json()["normalized_draft"]["allowed_weekdays"] == [0, 2, 4]
    assert preview.json()["authoritative_preview"]["state"] == "no_digest_context"
    assert saved.status_code == 200
    assert saved.json()["saved_settings"]["timezone"] == "Asia/Shanghai"
    assert saved.json()["authoritative_preview"]["state"] == "no_digest_context"
    assert admin_policy.status_code == 200
    official_policy = [
        item
        for item in admin_policy.json()
        if item["channel"] == ChannelType.OFFICIAL_ACCOUNT.value
    ][0]
    assert official_policy["policy"]["stale_days"] == 10
    assert self_service_bootstrap.status_code == 200


def test_auth_boundaries_between_mini_handoff_self_service_and_editor(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_handoff(monkeypatch)
    user, _binding, self_service_grant, mini_grant = setup_handoff_ready_user(
        client,
        operator_headers,
        email="mini-handoff-boundary@example.com",
    )
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}
    self_service_headers = {"Authorization": f"Bearer {self_service_grant['plain_text_token']}"}
    created = client.post("/mini/subscription-reserve/editor-handoff", headers=mini_headers)
    handoff_headers = {"Authorization": f"Bearer {created.json()['plain_text_token']}"}

    mini_to_editor = client.get("/subscription-editor/bootstrap", headers=mini_headers)
    self_service_to_mini = client.get("/mini/subscription-reserve", headers=self_service_headers)
    handoff_to_mini = client.get("/mini/subscription-reserve", headers=handoff_headers)
    handoff_to_self_service = client.get(
        "/subscription-self-service/editor-bootstrap",
        headers=handoff_headers,
    )

    assert mini_to_editor.status_code == 401
    assert self_service_to_mini.status_code == 401
    assert handoff_to_mini.status_code == 401
    assert handoff_to_self_service.status_code == 401


def test_admin_can_list_and_revoke_handoff_grants_and_revoked_or_expired_grants_are_rejected(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_handoff(monkeypatch)
    _user, _binding, _self_service_grant, mini_grant = setup_handoff_ready_user(
        client,
        operator_headers,
        email="mini-handoff-revoke@example.com",
    )
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}
    created = client.post("/mini/subscription-reserve/editor-handoff", headers=mini_headers)
    handoff_id = created.json()["handoff_grant"]["id"]
    handoff_headers = {"Authorization": f"Bearer {created.json()['plain_text_token']}"}

    listed = client.get("/admin/subscription-editor-handoff-grants", headers=operator_headers)
    revoked = client.post(
        f"/admin/subscription-editor-handoff-grants/{handoff_id}/revoke",
        headers=operator_headers,
    )
    revoked_bootstrap = client.get("/subscription-editor/bootstrap", headers=handoff_headers)

    assert listed.status_code == 200
    assert any(item["id"] == handoff_id for item in listed.json())
    assert revoked.status_code == 200
    assert revoked_bootstrap.status_code == 401

    enable_handoff(monkeypatch, ttl_minutes=-1)
    _user2, _binding2, _self_service_grant2, mini_grant2 = setup_handoff_ready_user(
        client,
        operator_headers,
        email="mini-handoff-expired@example.com",
    )
    mini_headers2 = {"Authorization": f"Bearer {mini_grant2['plain_text_token']}"}
    expired_created = client.post(
        "/mini/subscription-reserve/editor-handoff",
        headers=mini_headers2,
    )
    expired_headers = {"Authorization": f"Bearer {expired_created.json()['plain_text_token']}"}
    expired_bootstrap = client.get("/subscription-editor/bootstrap", headers=expired_headers)

    assert expired_created.status_code == 201
    assert expired_bootstrap.status_code == 401


def test_mini_subscription_reserve_includes_editor_handoff_reserve(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_handoff(monkeypatch)
    _user, _binding, _self_service_grant, mini_grant = setup_handoff_ready_user(
        client,
        operator_headers,
        email="mini-handoff-reserve@example.com",
    )
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}

    response = client.get("/mini/subscription-reserve", headers=mini_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["editor_handoff_reserve"]["supported"] is True
    assert payload["editor_handoff_reserve"]["enabled"] is True
    assert payload["editor_handoff_reserve"]["editable_via_current_mini_grant"] is False
    assert payload["editor_handoff_reserve"]["handoff_grant_required"] is True
    assert (
        "/subscription-editor/bootstrap"
        in payload["editor_handoff_reserve"]["supported_editor_endpoints"]
    )
