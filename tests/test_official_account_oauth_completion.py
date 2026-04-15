import hashlib
from urllib.parse import parse_qs, urlparse

import httpx

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.domain.enums import (
    ChannelType,
    MiniReadGrantType,
    OfficialAccountOAuthScope,
    OfficialAccountProviderMode,
    SubscriptionFrequency,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def configure_official_account_oauth_settings(
    monkeypatch,
    *,
    oauth_enabled: bool = True,
    fetch_userinfo: bool = True,
    app_id: str = "wx-official-app",
    callback_token: str = "callback-token",
) -> None:
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_PROVIDER_MODE",
        OfficialAccountProviderMode.DISABLED.value,
    )
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED", "true")
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_APP_ID", app_id)
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_APP_SECRET", "official-app-secret")
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_CALLBACK_TOKEN", callback_token)
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY", "callback-aes-key")
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_BINDING_REQUIRE_SIGNATURE_VALID",
        "true",
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_OAUTH_ENABLED",
        "true" if oauth_enabled else "false",
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_OAUTH_CALLBACK_PUBLIC_BASE_URL",
        "https://rp.example.com",
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_OAUTH_CALLBACK_PATH",
        "/integrations/wechat/official-account/oauth/callback",
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_OAUTH_DEFAULT_SCOPE",
        OfficialAccountOAuthScope.SNSAPI_BASE.value,
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_OAUTH_FETCH_USERINFO_WHEN_SCOPE_USERINFO",
        "true" if fetch_userinfo else "false",
    )
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_OAUTH_LANG", "zh_CN")
    get_settings.cache_clear()


def install_mock_official_account_oauth_http(
    monkeypatch,
    *,
    token_payload: dict | None = None,
    userinfo_payload: dict | None = None,
) -> dict[str, int]:
    calls = {"oauth_token": 0, "userinfo": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sns/oauth2/access_token"):
            calls["oauth_token"] += 1
            return httpx.Response(
                200,
                json=token_payload
                or {
                    "access_token": "oauth-access-token",
                    "refresh_token": "oauth-refresh-token",
                    "openid": "oauth-openid",
                    "scope": "snsapi_base",
                },
            )
        if request.url.path.endswith("/sns/userinfo"):
            calls["userinfo"] += 1
            return httpx.Response(
                200,
                json=userinfo_payload
                or {
                    "openid": "oauth-openid",
                    "nickname": "OAuth User",
                    "unionid": "oauth-unionid",
                },
            )
        raise AssertionError(f"unexpected OAuth HTTP request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "research_pulse_cn.services.official_account.create_official_account_http_client",
        lambda _settings: httpx.Client(transport=transport),
    )
    return calls


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "OAuth User",
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
    response = client.post(
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
    assert response.status_code in {201, 409}
    if response.status_code == 201:
        return response.json()
    listed = client.get(
        "/subscription-policies",
        headers=headers,
        params={"user_id": user_id},
    )
    assert listed.status_code == 200
    for item in listed.json():
        if item["channel"] == ChannelType.OFFICIAL_ACCOUNT.value:
            return item
    raise AssertionError("official_account policy was not found")


def create_self_service_grant(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/subscription-self-service-grants",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": ChannelType.OFFICIAL_ACCOUNT.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_mini_grant(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/mini-read-grants",
        headers=headers,
        json={
            "user_id": user_id,
            "grant_type": MiniReadGrantType.PREVIEW.value,
        },
    )
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
            "unionid": "unionid-secret",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Existing Binding",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_admin_handshake_session(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/official-account-binding-handshake-sessions",
        headers=headers,
        json={"user_id": user_id, "app_id": "wx-official-app"},
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
    timestamp: str = "1710000100",
    nonce: str = "nonce-100",
    event: str = "subscribe",
) -> None:
    signature = build_callback_signature("callback-token", timestamp, nonce)
    response = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=build_official_account_event_xml(openid=openid, event=event),
        headers={"Content-Type": "application/xml"},
    )
    assert response.status_code == 200


def extract_state(authorize_url: str) -> str:
    return parse_qs(urlparse(authorize_url).query)["state"][0]


def test_self_service_oauth_start_creates_authorize_url(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    user = create_user(client, operator_headers, email="oauth-start@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])

    response = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={
            "app_id": "wx-official-app",
            "display_label": "OAuth Start",
            "requested_scope": OfficialAccountOAuthScope.SNSAPI_USERINFO.value,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["status"] == "pending"
    assert payload["requested_scope"] == OfficialAccountOAuthScope.SNSAPI_USERINFO.value
    assert "connect/oauth2/authorize" in payload["authorize_url"]
    assert "state=" in payload["authorize_url"]


def test_admin_oauth_authorize_url_returns_authorize_url_for_existing_session(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    user = create_user(client, operator_headers, email="oauth-admin-url@example.com")
    session = create_admin_handshake_session(client, operator_headers, user_id=user["id"])

    response = client.post(
        f"/admin/official-account-binding-handshake-sessions/{session['session']['id']}/oauth-authorize-url",
        headers=operator_headers,
        json={"requested_scope": OfficialAccountOAuthScope.SNSAPI_USERINFO.value},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["requested_scope"] == OfficialAccountOAuthScope.SNSAPI_USERINFO.value
    assert "wechat_redirect" in payload["authorize_url"]


def test_oauth_disabled_blocks_authorize_url_issuance_cleanly(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch, oauth_enabled=False)
    user = create_user(client, operator_headers, email="oauth-disabled@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])

    response = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={"app_id": "wx-official-app"},
    )

    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]


def test_callback_with_invalid_state_fails_cleanly(
    client,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    install_mock_official_account_oauth_http(monkeypatch)

    response = client.get(
        "/integrations/wechat/official-account/oauth/callback",
        params={"code": "oauth-code-1", "state": "invalid-state"},
    )

    assert response.status_code == 404
    assert response.json()["action"] == "failed"


def test_callback_with_mocked_code_exchange_creates_new_binding_when_none_exists(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    calls = install_mock_official_account_oauth_http(
        monkeypatch,
        token_payload={
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "openid": "oauth-create-openid",
            "scope": OfficialAccountOAuthScope.SNSAPI_BASE.value,
        },
    )
    user = create_user(client, operator_headers, email="oauth-create-binding@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    started = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={"app_id": "wx-official-app"},
    ).json()

    callback = client.get(
        "/integrations/wechat/official-account/oauth/callback",
        params={"code": "oauth-code-create", "state": extract_state(started["authorize_url"])},
    )

    assert callback.status_code == 200
    payload = callback.json()
    assert payload["action"] == "claimed"
    assert payload["claimed_binding"]["subscribed"] is False
    assert calls["oauth_token"] == 1
    assert "access_token" not in payload["session"]
    assert "refresh_token" not in payload["session"]


def test_callback_reuses_existing_binding_when_same_user_appid_openid_exists(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    install_mock_official_account_oauth_http(
        monkeypatch,
        token_payload={
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "openid": "reuse-openid",
            "scope": OfficialAccountOAuthScope.SNSAPI_BASE.value,
        },
    )
    user = create_user(client, operator_headers, email="oauth-reuse@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    existing = create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="reuse-openid",
    )
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    started = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={"app_id": "wx-official-app"},
    ).json()

    callback = client.get(
        "/integrations/wechat/official-account/oauth/callback",
        params={"code": "oauth-code-reuse", "state": extract_state(started["authorize_url"])},
    )

    assert callback.status_code == 200
    assert callback.json()["claimed_binding"]["id"] == existing["id"]


def test_callback_conflicts_cleanly_when_same_appid_openid_belongs_to_different_user(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    install_mock_official_account_oauth_http(
        monkeypatch,
        token_payload={
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "openid": "conflict-openid",
            "scope": OfficialAccountOAuthScope.SNSAPI_BASE.value,
        },
    )
    other_user = create_user(client, operator_headers, email="oauth-conflict-other@example.com")
    create_official_account_binding(
        client,
        operator_headers,
        user_id=other_user["id"],
        openid="conflict-openid",
    )
    user = create_user(client, operator_headers, email="oauth-conflict-target@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    started = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={"app_id": "wx-official-app"},
    ).json()

    callback = client.get(
        "/integrations/wechat/official-account/oauth/callback",
        params={"code": "oauth-code-conflict", "state": extract_state(started["authorize_url"])},
    )
    oauth_status = client.get(
        "/subscription-self-service/wechat-binding-reserve/oauth-status",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
    )

    assert callback.status_code == 409
    assert callback.json()["action"] == "failed"
    assert "different user" in callback.json()["detail"]
    assert oauth_status.status_code == 200
    assert oauth_status.json()["session"]["status"] == "conflicted"


def test_callback_links_existing_subscribe_callback_evidence_and_marks_subscribed_true(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    install_mock_official_account_oauth_http(
        monkeypatch,
        token_payload={
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "openid": "evidence-openid",
            "scope": OfficialAccountOAuthScope.SNSAPI_BASE.value,
        },
    )
    user = create_user(client, operator_headers, email="oauth-evidence@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    started = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={"app_id": "wx-official-app"},
    ).json()
    ingest_callback(client, openid="evidence-openid")

    callback = client.get(
        "/integrations/wechat/official-account/oauth/callback",
        params={"code": "oauth-code-evidence", "state": extract_state(started["authorize_url"])},
    )

    assert callback.status_code == 200
    payload = callback.json()
    assert payload["callback_evidence_linked"] is True
    assert payload["claimed_binding"]["subscribed"] is True
    assert payload["callback_event"]["linked_binding_id"] == payload["claimed_binding"]["id"]


def test_snsapi_userinfo_path_fetches_userinfo_when_configured_and_scope_allows(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch, fetch_userinfo=True)
    calls = install_mock_official_account_oauth_http(
        monkeypatch,
        token_payload={
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "openid": "userinfo-openid",
            "scope": OfficialAccountOAuthScope.SNSAPI_USERINFO.value,
        },
        userinfo_payload={
            "openid": "userinfo-openid",
            "nickname": "User Info",
            "unionid": "userinfo-unionid",
        },
    )
    user = create_user(client, operator_headers, email="oauth-userinfo@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    started = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {grant['plain_text_token']}"},
        json={
            "app_id": "wx-official-app",
            "requested_scope": OfficialAccountOAuthScope.SNSAPI_USERINFO.value,
        },
    ).json()

    callback = client.get(
        "/integrations/wechat/official-account/oauth/callback",
        params={"code": "oauth-code-userinfo", "state": extract_state(started["authorize_url"])},
    )

    assert callback.status_code == 200
    assert callback.json()["userinfo_fetched"] is True
    assert calls["oauth_token"] == 1
    assert calls["userinfo"] == 1


def test_admin_oauth_status_and_mini_reserve_reflect_oauth_enabled(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch, oauth_enabled=True)
    user = create_user(client, operator_headers, email="oauth-status@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    mini_grant = create_mini_grant(client, operator_headers, user_id=user["id"])

    admin_status = client.get("/admin/official-account/oauth-status", headers=operator_headers)
    mini_reserve = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )

    assert admin_status.status_code == 200
    assert admin_status.json()["oauth_enabled"] is True
    assert mini_reserve.status_code == 200
    assert mini_reserve.json()["binding_handoff_reserve"]["oauth_enabled"] is True
    assert mini_reserve.json()["self_service_reserve"]["oauth_enabled"] is True


def test_mini_and_self_service_auth_boundaries_remain_separate_for_oauth_endpoints(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_oauth_settings(monkeypatch)
    user = create_user(client, operator_headers, email="oauth-boundary@example.com")
    ensure_official_account_policy(client, operator_headers, user_id=user["id"])
    mini_grant = create_mini_grant(client, operator_headers, user_id=user["id"])
    self_service_grant = create_self_service_grant(client, operator_headers, user_id=user["id"])

    mini_on_self_service = client.post(
        "/subscription-self-service/wechat-binding-reserve/oauth-start",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
        json={"app_id": "wx-official-app"},
    )
    mini_on_self_service_status = client.get(
        "/subscription-self-service/wechat-binding-reserve/oauth-status",
        headers={"Authorization": f"Bearer {mini_grant['plain_text_token']}"},
    )
    self_service_on_mini = client.get(
        "/mini/subscription-reserve",
        headers={"Authorization": f"Bearer {self_service_grant['plain_text_token']}"},
    )

    assert mini_on_self_service.status_code == 401
    assert mini_on_self_service_status.status_code == 401
    assert self_service_on_mini.status_code == 401
