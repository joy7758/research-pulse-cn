from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
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
            "name": "Self Service User",
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
            "last_touch_at": (utcnow() - timedelta(days=7)).isoformat(),
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
        (15, 93, newer),
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


def ensure_policy(
    client,
    headers,
    *,
    user_id: str,
    channel: str,
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
        if existing["channel"] != channel:
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
            "channel": channel,
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
            "unionid": "unionid-should-not-leak",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "OA Binding",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_digest_issue(client, headers, *, user_id: str) -> dict:
    paper = create_paper(client, headers, user_id=user_id, title="Self Service Digest Paper")
    add_signal_pair(client, headers, paper_id=paper["id"])
    run = client.post(f"/pulse/run/{user_id}", headers=headers)
    assert run.status_code == 200
    response = client.get("/admin/digest-issues", headers=headers, params={"user_id": user_id})
    assert response.status_code == 200
    return response.json()[0]


def create_self_service_grant(
    client,
    headers,
    *,
    user_id: str,
    binding_id: str | None = None,
    expires_at: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "user_id": user_id,
        "channel": ChannelType.OFFICIAL_ACCOUNT.value,
    }
    if binding_id is not None:
        payload["binding_id"] = binding_id
    if expires_at is not None:
        payload["expires_at"] = expires_at
    response = client.post(
        "/admin/subscription-self-service-grants",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_operator_can_create_self_service_grant_and_receive_plaintext_token_once(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="self-service-create@example.com")

    created = create_self_service_grant(client, operator_headers, user_id=user["id"])
    listed = client.get("/admin/subscription-self-service-grants", headers=operator_headers)

    assert created["grant"]["user_id"] == user["id"]
    assert created["plain_text_token"]
    assert "plain_text_token" not in listed.json()[0]


def test_viewer_cannot_create_self_service_grant(client, operator_headers, viewer_headers) -> None:
    user = create_user(client, operator_headers, email="self-service-viewer@example.com")

    response = client.post(
        "/admin/subscription-self-service-grants",
        headers=viewer_headers,
        json={"user_id": user["id"], "channel": ChannelType.OFFICIAL_ACCOUNT.value},
    )

    assert response.status_code == 403


def test_self_service_token_can_access_only_self_service_routes(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="self-service-access@example.com")
    created = create_self_service_grant(client, operator_headers, user_id=user["id"])
    token_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    bootstrap = client.get("/subscription-self-service/bootstrap", headers=token_headers)
    admin_route = client.get("/admin/admin-accounts", headers=token_headers)
    ops_route = client.get("/ops/metrics", headers=token_headers)
    sync_route = client.get("/sync/me", headers=token_headers)
    mini_route = client.get("/mini/bootstrap", headers=token_headers)
    business_route = client.get("/users", headers=token_headers)

    assert bootstrap.status_code == 200
    assert admin_route.status_code == 401
    assert ops_route.status_code == 401
    assert sync_route.status_code == 401
    assert mini_route.status_code == 401
    assert business_route.status_code == 401


def test_revoked_and_expired_self_service_grants_are_rejected(
    client,
    operator_headers,
) -> None:
    revoked_user = create_user(client, operator_headers, email="self-service-revoke@example.com")
    revoked = create_self_service_grant(client, operator_headers, user_id=revoked_user["id"])
    revoke = client.post(
        f"/admin/subscription-self-service-grants/{revoked['grant']['id']}/revoke",
        headers=operator_headers,
    )
    revoked_response = client.get(
        "/subscription-self-service/bootstrap",
        headers={"Authorization": f"Bearer {revoked['plain_text_token']}"},
    )

    expired_user = create_user(client, operator_headers, email="self-service-expired@example.com")
    expired = create_self_service_grant(
        client,
        operator_headers,
        user_id=expired_user["id"],
        expires_at=(utcnow() - timedelta(minutes=1)).isoformat(),
    )
    expired_response = client.get(
        "/subscription-self-service/bootstrap",
        headers={"Authorization": f"Bearer {expired['plain_text_token']}"},
    )

    assert revoke.status_code == 200
    assert revoked_response.status_code == 401
    assert expired_response.status_code == 401


def test_bootstrap_returns_safe_binding_summary_without_openid_or_unionid(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="self-service-bootstrap@example.com")
    digest_issue = create_digest_issue(client, operator_headers, user_id=user["id"])
    ensure_policy(
        client,
        operator_headers,
        user_id=user["id"],
        channel=ChannelType.OFFICIAL_ACCOUNT.value,
        policy={"timezone": "UTC", "skip_if_no_today_focus": True},
    )
    binding = create_official_account_binding(
        client,
        operator_headers,
        user_id=user["id"],
        openid="oa-bootstrap-openid",
    )
    created = create_self_service_grant(
        client,
        operator_headers,
        user_id=user["id"],
        binding_id=binding["id"],
    )

    response = client.get(
        "/subscription-self-service/bootstrap",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["binding"]["id"] == binding["id"]
    assert "openid" not in payload["binding"]
    assert "unionid" not in payload["binding"]
    assert payload["latest_digest_issue"]["id"] == digest_issue["id"]


def test_settings_read_and_patch_preserve_unknown_policy_keys(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="self-service-settings@example.com")
    policy = ensure_policy(
        client,
        operator_headers,
        user_id=user["id"],
        channel=ChannelType.OFFICIAL_ACCOUNT.value,
        policy={
            "timezone": "UTC",
            "allowed_weekdays": [0, 1, 2],
            "custom_existing_key": "preserve-me",
        },
    )
    created = create_self_service_grant(client, operator_headers, user_id=user["id"])
    token_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    settings = client.get("/subscription-self-service/settings", headers=token_headers)
    patched = client.patch(
        "/subscription-self-service/settings",
        headers=token_headers,
        json={
            "allowed_weekdays": [0, 2, 4],
            "minimum_selected_cards": 2,
            "skip_if_no_today_focus": True,
        },
    )
    refreshed_policy = client.get(
        f"/subscription-policies/{policy['id']}",
        headers=operator_headers,
    )

    assert settings.status_code == 200
    assert settings.json()["subscription_policy_id"] == policy["id"]
    assert patched.status_code == 200
    assert patched.json()["allowed_weekdays"] == [0, 2, 4]
    assert patched.json()["minimum_selected_cards"] == 2
    assert patched.json()["skip_if_no_today_focus"] is True
    assert refreshed_policy.status_code == 200
    assert refreshed_policy.json()["policy"]["custom_existing_key"] == "preserve-me"


def test_settings_patch_can_upsert_official_account_policy_if_missing(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="self-service-upsert@example.com")
    created = create_self_service_grant(client, operator_headers, user_id=user["id"])
    token_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    patched = client.patch(
        "/subscription-self-service/settings",
        headers=token_headers,
        json={
            "enabled": False,
            "timezone": "Asia/Shanghai",
            "allowed_weekdays": [0, 1, 2, 3, 4],
            "minimum_selected_cards": 1,
        },
    )
    policies = client.get(
        "/subscription-policies",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )

    assert patched.status_code == 200
    assert patched.json()["subscription_policy_id"] is not None
    official_policy = next(
        policy
        for policy in policies.json()
        if policy["channel"] == ChannelType.OFFICIAL_ACCOUNT.value
    )
    assert official_policy["enabled"] is False
    assert official_policy["frequency"] == SubscriptionFrequency.DAILY.value
    assert official_policy["policy"]["timezone"] == "Asia/Shanghai"


def test_delivery_control_preview_returns_authoritative_evaluator_output(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="self-service-preview@example.com")
    digest_issue = create_digest_issue(client, operator_headers, user_id=user["id"])
    ensure_policy(
        client,
        operator_headers,
        user_id=user["id"],
        channel=ChannelType.OFFICIAL_ACCOUNT.value,
        policy={"timezone": "UTC", "minimum_selected_cards": 5},
    )
    created = create_self_service_grant(client, operator_headers, user_id=user["id"])

    response = client.get(
        "/subscription-self-service/delivery-control-preview",
        headers={"Authorization": f"Bearer {created['plain_text_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "skipped"
    assert "insufficient_selected_cards" in payload["reason_codes"]
    assert payload["latest_digest_issue"]["id"] == digest_issue["id"]
