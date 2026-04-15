import hashlib
from datetime import timedelta

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    MiniReadGrantType,
    OfficialAccountProviderMode,
    SubscriptionFrequency,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def configure_official_account_settings(
    monkeypatch,
    *,
    provider_mode: str = OfficialAccountProviderMode.DISABLED.value,
    callback_enabled: bool = True,
    app_id: str = "wx-official-app",
    callback_token: str = "callback-token",
    require_signature_valid: bool = True,
) -> None:
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_PROVIDER_MODE", provider_mode)
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED",
        "true" if callback_enabled else "false",
    )
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_APP_ID", app_id)
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_CALLBACK_TOKEN", callback_token)
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY", "callback-aes-key")
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_BINDING_REQUIRE_SIGNATURE_VALID",
        "true" if require_signature_valid else "false",
    )
    get_settings.cache_clear()


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Handshake User",
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


def ensure_official_account_policy(client, headers, *, user_id: str) -> dict:
    response = client.get(
        "/subscription-policies",
        headers=headers,
        params={"user_id": user_id},
    )
    assert response.status_code == 200
    for existing in response.json():
        if existing["channel"] == ChannelType.OFFICIAL_ACCOUNT.value:
            return existing
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
            "policy": {"timezone": "UTC"},
        },
    )
    assert created.status_code == 201
    return created.json()


def create_self_service_grant(
    client, headers, *, user_id: str, binding_id: str | None = None
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


def create_mini_grant(client, headers, *, user_id: str, binding_id: str | None = None) -> dict:
    payload: dict[str, object] = {
        "user_id": user_id,
        "grant_type": MiniReadGrantType.PREVIEW.value,
    }
    if binding_id is not None:
        payload["binding_id"] = binding_id
    response = client.post("/admin/mini-read-grants", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def create_official_account_binding(client, headers, *, user_id: str, openid: str) -> dict:
    ensure_official_account_policy(client, headers, user_id=user_id)
    response = client.post(
        "/admin/wechat-bindings",
        headers=headers,
        json={
            "user_id": user_id,
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": openid,
            "unionid": "unionid-should-not-leak",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Official Account Binding",
        },
    )
    assert response.status_code == 201
    return response.json()


def build_callback_signature(token: str, timestamp: str, nonce: str) -> str:
    return hashlib.sha1("".join(sorted([token, timestamp, nonce])).encode("utf-8")).hexdigest()


def build_official_account_event_xml(
    *,
    openid: str,
    event: str = "subscribe",
    event_time: int = 1_710_000_000,
) -> str:
    return (
        "<xml>"
        "<ToUserName><![CDATA[gh_test_official]]></ToUserName>"
        f"<FromUserName><![CDATA[{openid}]]></FromUserName>"
        f"<CreateTime>{event_time}</CreateTime>"
        "<MsgType><![CDATA[event]]></MsgType>"
        f"<Event><![CDATA[{event}]]></Event>"
        "</xml>"
    )


def ingest_callback(
    client,
    *,
    openid: str,
    signature_token: str = "callback-token",
    timestamp: str = "1710000010",
    nonce: str = "nonce-010",
    event: str = "subscribe",
    signature_override: str | None = None,
) -> None:
    signature = signature_override or build_callback_signature(signature_token, timestamp, nonce)
    response = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=build_official_account_event_xml(openid=openid, event=event),
        headers={"Content-Type": "application/xml"},
    )
    assert response.status_code == 200


def create_handshake_session(
    client, headers, *, user_id: str, self_service_grant_id: str | None = None
) -> dict:
    payload: dict[str, object] = {"user_id": user_id, "app_id": "wx-official-app"}
    if self_service_grant_id is not None:
        payload["self_service_grant_id"] = self_service_grant_id
    response = client.post(
        "/admin/official-account-binding-handshake-sessions",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_admin_can_create_handshake_session_and_viewer_cannot(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-admin@example.com")

    created = create_handshake_session(client, operator_headers, user_id=user["id"])
    denied = client.post(
        "/admin/official-account-binding-handshake-sessions",
        headers=viewer_headers,
        json={"user_id": user["id"], "app_id": "wx-official-app"},
    )

    assert created["session"]["status"] == "pending"
    assert created["plain_text_state_token"]
    assert denied.status_code == 403


def test_candidate_listing_returns_only_unmatched_eligible_subscribe_events(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch, require_signature_valid=True)
    user = create_user(client, operator_headers, email="handshake-candidates@example.com")
    create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="bound-openid",
    )

    ingest_callback(client, openid="eligible-openid", timestamp="1710000011", nonce="nonce-011")
    ingest_callback(
        client,
        openid="unsubscribe-openid",
        timestamp="1710000012",
        nonce="nonce-012",
        event="unsubscribe",
    )
    ingest_callback(client, openid="bound-openid", timestamp="1710000013", nonce="nonce-013")

    response = client.get(
        "/admin/official-account-binding-reconciliation/candidates",
        headers=operator_headers,
        params={"app_id": "wx-official-app"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["event_type"] == "subscribe"
    assert payload[0]["signature_valid"] is True
    assert payload[0]["linked_binding_id"] is None
    assert payload[0]["masked_openid"] != "eligible-openid"


def test_claim_creates_new_binding_from_eligible_callback_event(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-claim-create@example.com")
    session = create_handshake_session(client, operator_headers, user_id=user["id"])
    ingest_callback(client, openid="claim-create-openid", timestamp="1710000015", nonce="nonce-015")
    candidates = client.get(
        "/admin/official-account-binding-reconciliation/candidates",
        headers=operator_headers,
        params={"app_id": "wx-official-app"},
    ).json()

    claimed = client.post(
        f"/admin/official-account-binding-handshake-sessions/{session['session']['id']}/claim",
        headers=operator_headers,
        json={"callback_event_id": candidates[0]["callback_event_id"]},
    )

    assert claimed.status_code == 200
    payload = claimed.json()
    assert payload["session"]["status"] == "claimed"
    assert payload["claimed_binding"]["channel_type"] == "official_account"
    assert "openid" not in payload["claimed_binding"]
    assert payload["callback_event"]["linked_binding_id"] == payload["claimed_binding"]["id"]


def test_claim_reuses_existing_binding_for_same_user_app_id_and_openid(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-claim-reuse@example.com")
    session = create_handshake_session(client, operator_headers, user_id=user["id"])
    ingest_callback(client, openid="reuse-openid", timestamp="1710000016", nonce="nonce-016")
    existing_binding = create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="reuse-openid",
    )
    candidates = client.get(
        "/admin/official-account-binding-reconciliation/candidates",
        headers=operator_headers,
        params={"app_id": "wx-official-app"},
    ).json()

    claimed = client.post(
        f"/admin/official-account-binding-handshake-sessions/{session['session']['id']}/claim",
        headers=operator_headers,
        json={"callback_event_id": candidates[0]["callback_event_id"]},
    )

    assert claimed.status_code == 200
    assert claimed.json()["claimed_binding"]["id"] == existing_binding["id"]


def test_claim_fails_cleanly_when_openid_is_already_bound_to_different_user(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    claimant = create_user(client, operator_headers, email="handshake-claimant@example.com")
    other_user = create_user(client, operator_headers, email="handshake-other@example.com")
    session = create_handshake_session(client, operator_headers, user_id=claimant["id"])
    ingest_callback(client, openid="conflict-openid", timestamp="1710000017", nonce="nonce-017")
    create_official_account_binding(
        client,
        operator_headers,
        user_id=other_user["id"],
        openid="conflict-openid",
    )
    candidates = client.get(
        "/admin/official-account-binding-reconciliation/candidates",
        headers=operator_headers,
        params={"app_id": "wx-official-app"},
    ).json()

    claimed = client.post(
        f"/admin/official-account-binding-handshake-sessions/{session['session']['id']}/claim",
        headers=operator_headers,
        json={"callback_event_id": candidates[0]["callback_event_id"]},
    )

    assert claimed.status_code == 409
    assert "different user" in claimed.json()["detail"]


def test_self_service_grant_can_bootstrap_and_manage_own_handshake_session(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-self-service@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    token_headers = {"Authorization": f"Bearer {grant['plain_text_token']}"}
    ingest_callback(client, openid="self-service-openid", timestamp="1710000018", nonce="nonce-018")

    bootstrap = client.get(
        "/subscription-self-service/wechat-binding-reserve/bootstrap",
        headers=token_headers,
    )
    created = client.post(
        "/subscription-self-service/wechat-binding-reserve/session",
        headers=token_headers,
        json={"app_id": "wx-official-app", "display_label": "My OA Handshake"},
    )
    fetched = client.get(
        "/subscription-self-service/wechat-binding-reserve/session",
        headers=token_headers,
    )
    cancelled = client.post(
        "/subscription-self-service/wechat-binding-reserve/session/cancel",
        headers=token_headers,
    )

    assert bootstrap.status_code == 200
    assert bootstrap.json()["candidate_count_hint"] == 1
    assert bootstrap.json()["binding"] is None
    assert created.status_code == 201
    assert created.json()["plain_text_state_token"]
    assert fetched.status_code == 200
    assert fetched.json()["session"]["status"] == "matched"
    assert cancelled.status_code == 200
    assert cancelled.json()["session"]["status"] == "cancelled"


def test_self_service_grant_cannot_claim_and_auth_boundaries_remain_separate(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-auth-boundary@example.com")
    self_service_grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    mini_grant = create_mini_grant(client, operator_headers, user_id=user["id"])
    session = create_handshake_session(
        client,
        operator_headers,
        user_id=user["id"],
        self_service_grant_id=self_service_grant["grant"]["id"],
    )
    ingest_callback(
        client, openid="auth-boundary-openid", timestamp="1710000019", nonce="nonce-019"
    )
    candidates = client.get(
        "/admin/official-account-binding-reconciliation/candidates",
        headers=operator_headers,
        params={"app_id": "wx-official-app"},
    ).json()

    self_service_claim = client.post(
        f"/admin/official-account-binding-handshake-sessions/{session['session']['id']}/claim",
        headers={"Authorization": f"Bearer {self_service_grant['plain_text_token']}"},
        json={"callback_event_id": candidates[0]["callback_event_id"]},
    )
    mini_on_self_service = client.get(
        "/subscription-self-service/wechat-binding-reserve/bootstrap",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )
    self_service_on_mini = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {self_service_grant['plain_text_token']}"},
    )

    assert self_service_claim.status_code == 401
    assert mini_on_self_service.status_code == 401
    assert self_service_on_mini.status_code == 401


def test_mini_subscription_reserve_includes_read_only_binding_handoff_reserve(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-mini@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    self_service_grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    create_handshake_session(
        client,
        operator_headers,
        user_id=user["id"],
        self_service_grant_id=self_service_grant["grant"]["id"],
    )
    mini_grant = create_mini_grant(client, operator_headers, user_id=user["id"])

    response = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["binding_handoff_reserve"]["supported"] is True
    assert payload["binding_handoff_reserve"]["oauth_enabled"] is False
    assert payload["binding_handoff_reserve"]["active_session_status"] == "pending"
    assert payload["binding_handoff_reserve"]["separate_self_service_grant_required"] is True


def test_self_service_and_mini_summaries_never_expose_openid_or_unionid(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-safe-summaries@example.com")
    binding = create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="safe-summary-openid",
    )
    self_service_grant = create_self_service_grant(
        client,
        operator_headers,
        user_id=user["id"],
        binding_id=binding["id"],
    )
    mini_grant = create_mini_grant(
        client, operator_headers, user_id=user["id"], binding_id=binding["id"]
    )

    self_service_bootstrap = client.get(
        "/subscription-self-service/wechat-binding-reserve/bootstrap",
        headers={"Authorization": f"Bearer {self_service_grant['plain_text_token']}"},
    )
    mini_reserve = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )

    assert self_service_bootstrap.status_code == 200
    assert mini_reserve.status_code == 200
    assert "openid" not in self_service_bootstrap.json()["binding"]
    assert "unionid" not in self_service_bootstrap.json()["binding"]
    assert "openid" not in mini_reserve.json()["official_account_binding"]
    assert "unionid" not in mini_reserve.json()["official_account_binding"]


def test_expired_handshake_session_is_not_treated_as_active(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(monkeypatch)
    user = create_user(client, operator_headers, email="handshake-expired@example.com")
    created = client.post(
        "/admin/official-account-binding-handshake-sessions",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "app_id": "wx-official-app",
            "expires_at": (utcnow() - timedelta(minutes=1)).isoformat(),
        },
    )
    session_id = created.json()["session"]["id"]

    detail = client.get(
        f"/admin/official-account-binding-handshake-sessions/{session_id}",
        headers=operator_headers,
    )

    assert detail.status_code == 200
    assert detail.json()["status"] == "expired"
