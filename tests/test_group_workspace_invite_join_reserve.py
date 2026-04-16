from __future__ import annotations

import json

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.domain.enums import (
    ChannelType,
    GroupWorkspaceInviteClaimStatus,
    GroupWorkspaceInviteGrantStatus,
    GroupWorkspaceInviteRole,
    GroupWorkspaceMemberRole,
    MiniReadGrantType,
)


def enable_invites(
    monkeypatch,
    *,
    enabled: bool = True,
    default_max_claims: int = 1,
    ttl_hours: int = 72,
    public_bootstrap_enabled: bool = True,
) -> None:
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_INVITES_ENABLED",
        "true" if enabled else "false",
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_INVITE_DEFAULT_MAX_CLAIMS",
        str(default_max_claims),
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_INVITE_TTL_HOURS",
        str(ttl_hours),
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_INVITE_PUBLIC_BOOTSTRAP_ENABLED",
        "true" if public_bootstrap_enabled else "false",
    )
    get_settings.cache_clear()


def create_user(client, headers, *, email: str, name: str = "Invite User") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": name,
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


def create_workspace(client, headers, *, slug: str, name: str) -> dict:
    response = client.post(
        "/admin/group-workspaces",
        headers=headers,
        json={"slug": slug, "name": name, "description": f"{name} description"},
    )
    assert response.status_code == 201
    return response.json()


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


def add_workspace_member(client, headers, *, workspace_id: str, user_id: str, role: str) -> dict:
    response = client.post(
        f"/admin/group-workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": role},
    )
    assert response.status_code == 201
    return response.json()


def create_invite_grant(
    client,
    headers,
    *,
    workspace_id: str,
    role_to_assign: str = GroupWorkspaceInviteRole.VIEWER.value,
    max_claims: int | None = None,
) -> dict:
    payload: dict[str, object] = {
        "workspace_id": workspace_id,
        "role_to_assign": role_to_assign,
    }
    if max_claims is not None:
        payload["max_claims"] = max_claims
    response = client.post(
        "/admin/group-workspace-invite-grants",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_operator_can_create_invite_grant_and_viewer_cannot_mutate(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    enable_invites(monkeypatch)
    workspace = create_workspace(client, operator_headers, slug="invite-space", name="Invite Space")

    created = create_invite_grant(client, operator_headers, workspace_id=workspace["id"])
    listed = client.get("/admin/group-workspace-invite-grants", headers=viewer_headers)
    viewer_create = client.post(
        "/admin/group-workspace-invite-grants",
        headers=viewer_headers,
        json={
            "workspace_id": workspace["id"],
            "role_to_assign": GroupWorkspaceInviteRole.VIEWER.value,
        },
    )

    assert created["grant"]["status"] == GroupWorkspaceInviteGrantStatus.ACTIVE.value
    assert created["plain_text_token"]
    assert listed.status_code == 200
    assert any(item["id"] == created["grant"]["id"] for item in listed.json())
    assert viewer_create.status_code == 403


def test_public_bootstrap_returns_safe_summary_and_invites_disabled_blocks_flows(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_invites(monkeypatch)
    user = create_user(client, operator_headers, email="invite-disabled@example.com")
    grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    workspace = create_workspace(
        client,
        operator_headers,
        slug="invite-bootstrap",
        name="Invite Bootstrap",
    )
    invite = create_invite_grant(client, operator_headers, workspace_id=workspace["id"])
    self_service_headers = {"Authorization": f"Bearer {grant['plain_text_token']}"}

    bootstrap = client.get(f"/workspace-invites/{invite['plain_text_token']}/bootstrap")
    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload["workspace"]["slug"] == workspace["slug"]
    assert payload["invite"]["role_to_assign"] == GroupWorkspaceInviteRole.VIEWER.value
    serialized = json.dumps(payload)
    assert "openid" not in serialized
    assert "unionid" not in serialized
    assert "/Users/" not in serialized

    enable_invites(monkeypatch, enabled=False)
    disabled_create = client.post(
        "/admin/group-workspace-invite-grants",
        headers=operator_headers,
        json={
            "workspace_id": workspace["id"],
            "role_to_assign": GroupWorkspaceInviteRole.VIEWER.value,
        },
    )
    disabled_bootstrap = client.get(f"/workspace-invites/{invite['plain_text_token']}/bootstrap")
    disabled_preview = client.get(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim-preview",
        headers=self_service_headers,
    )
    disabled_claim = client.post(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
        headers=self_service_headers,
    )

    assert disabled_create.status_code == 422
    assert disabled_bootstrap.status_code == 422
    assert disabled_preview.status_code == 200
    assert disabled_preview.json()["reason_codes"] == ["invites_disabled"]
    assert disabled_claim.status_code == 200
    assert disabled_claim.json()["action"] == "rejected"
    assert disabled_claim.json()["invite_claim"] is None


def test_claim_preview_reports_already_member_and_self_service_memberships_are_listed(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_invites(monkeypatch)
    user = create_user(client, operator_headers, email="invite-member@example.com")
    workspace = create_workspace(
        client,
        operator_headers,
        slug="invite-member",
        name="Invite Member",
    )
    add_workspace_member(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        user_id=user["id"],
        role=GroupWorkspaceMemberRole.EDITOR.value,
    )
    invite = create_invite_grant(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        role_to_assign=GroupWorkspaceInviteRole.VIEWER.value,
        max_claims=3,
    )
    self_service_grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    self_service_headers = {"Authorization": f"Bearer {self_service_grant['plain_text_token']}"}

    preview = client.get(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim-preview",
        headers=self_service_headers,
    )
    memberships = client.get(
        "/subscription-self-service/workspace-memberships",
        headers=self_service_headers,
    )

    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["can_claim"] is False
    assert preview_payload["reason_codes"] == ["already_member"]
    assert preview_payload["current_membership"]["workspace_summary"]["id"] == workspace["id"]
    assert memberships.status_code == 200
    assert memberships.json()[0]["workspace_summary"]["slug"] == workspace["slug"]


def test_self_service_claim_creates_membership_and_repeat_claim_returns_already_member(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_invites(monkeypatch, default_max_claims=3)
    user = create_user(client, operator_headers, email="invite-claim@example.com")
    workspace = create_workspace(client, operator_headers, slug="invite-claim", name="Invite Claim")
    invite = create_invite_grant(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        role_to_assign=GroupWorkspaceInviteRole.EDITOR.value,
        max_claims=3,
    )
    self_service_grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    self_service_headers = {"Authorization": f"Bearer {self_service_grant['plain_text_token']}"}

    claimed = client.post(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
        headers=self_service_headers,
    )
    repeated = client.post(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
        headers=self_service_headers,
    )
    claims = client.get(
        "/admin/group-workspace-invite-claims",
        headers=operator_headers,
        params={"workspace_id": workspace["id"], "user_id": user["id"]},
    )

    assert claimed.status_code == 200
    claimed_payload = claimed.json()
    assert claimed_payload["action"] == "claimed"
    assert claimed_payload["membership"]["role"] == GroupWorkspaceMemberRole.EDITOR.value
    assert (
        claimed_payload["invite_claim"]["claim_status"]
        == GroupWorkspaceInviteClaimStatus.CLAIMED.value
    )

    assert repeated.status_code == 200
    repeated_payload = repeated.json()
    assert repeated_payload["action"] == "already_member"
    assert (
        repeated_payload["invite_claim"]["claim_status"]
        == GroupWorkspaceInviteClaimStatus.ALREADY_MEMBER.value
    )

    assert claims.status_code == 200
    assert len(claims.json()) == 1


def test_exhausted_revoked_and_expired_invites_reject_claims_and_owner_role_is_not_assignable(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_invites(monkeypatch, default_max_claims=1)
    workspace = create_workspace(
        client,
        operator_headers,
        slug="invite-rejections",
        name="Invite Rejections",
    )
    first_user = create_user(client, operator_headers, email="invite-first@example.com")
    second_user = create_user(client, operator_headers, email="invite-second@example.com")
    third_user = create_user(client, operator_headers, email="invite-third@example.com")

    first_grant = create_self_service_grant(client, operator_headers, user_id=first_user["id"])
    second_grant = create_self_service_grant(client, operator_headers, user_id=second_user["id"])
    third_grant = create_self_service_grant(client, operator_headers, user_id=third_user["id"])

    exhausted_invite = create_invite_grant(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        max_claims=1,
    )
    first_headers = {"Authorization": f"Bearer {first_grant['plain_text_token']}"}
    second_headers = {"Authorization": f"Bearer {second_grant['plain_text_token']}"}
    first_claim = client.post(
        f"/subscription-self-service/workspace-invites/{exhausted_invite['plain_text_token']}/claim",
        headers=first_headers,
    )
    second_claim = client.post(
        f"/subscription-self-service/workspace-invites/{exhausted_invite['plain_text_token']}/claim",
        headers=second_headers,
    )

    revoked_invite = create_invite_grant(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        max_claims=2,
    )
    revoked = client.post(
        f"/admin/group-workspace-invite-grants/{revoked_invite['grant']['id']}/revoke",
        headers=operator_headers,
    )
    revoked_claim = client.post(
        f"/subscription-self-service/workspace-invites/{revoked_invite['plain_text_token']}/claim",
        headers={"Authorization": f"Bearer {third_grant['plain_text_token']}"},
    )

    enable_invites(monkeypatch, default_max_claims=1, ttl_hours=-1)
    expired_invite = create_invite_grant(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        max_claims=1,
    )
    expired_claim = client.post(
        f"/subscription-self-service/workspace-invites/{expired_invite['plain_text_token']}/claim",
        headers={"Authorization": f"Bearer {third_grant['plain_text_token']}"},
    )

    owner_role = client.post(
        "/admin/group-workspace-invite-grants",
        headers=operator_headers,
        json={
            "workspace_id": workspace["id"],
            "role_to_assign": GroupWorkspaceMemberRole.OWNER.value,
        },
    )

    assert first_claim.status_code == 200
    assert first_claim.json()["action"] == "claimed"
    assert second_claim.status_code == 200
    assert second_claim.json()["action"] == "rejected"
    assert second_claim.json()["invite_claim"]["reason_codes"] == ["invite_exhausted"]
    assert revoked.status_code == 200
    assert revoked_claim.status_code == 200
    assert revoked_claim.json()["invite_claim"]["reason_codes"] == ["invite_revoked"]
    assert expired_claim.status_code == 200
    assert expired_claim.json()["invite_claim"]["reason_codes"] == ["invite_expired"]
    assert owner_role.status_code == 422


def test_mini_grant_cannot_claim_workspace_membership_and_self_service_cannot_access_admin_invites(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_invites(monkeypatch)
    user = create_user(client, operator_headers, email="invite-mini@example.com")
    workspace = create_workspace(client, operator_headers, slug="invite-mini", name="Invite Mini")
    invite = create_invite_grant(client, operator_headers, workspace_id=workspace["id"])
    self_service_grant = create_self_service_grant(client, operator_headers, user_id=user["id"])
    mini_grant = create_mini_grant(client, operator_headers, user_id=user["id"])
    self_service_headers = {"Authorization": f"Bearer {self_service_grant['plain_text_token']}"}
    mini_headers = {"Authorization": f"Bearer {mini_grant['plain_text_token']}"}

    mini_preview = client.get(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim-preview",
        headers=mini_headers,
    )
    mini_claim = client.post(
        f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
        headers=mini_headers,
    )
    self_service_to_admin = client.get(
        "/admin/group-workspace-invite-grants",
        headers=self_service_headers,
    )
    mini_reserve = client.get("/mini/subscription-reserve", headers=mini_headers)

    assert mini_preview.status_code == 401
    assert mini_claim.status_code == 401
    assert self_service_to_admin.status_code == 401
    assert mini_reserve.status_code == 200
    assert mini_reserve.json()["workspace_invite_reserve"]["supported"] is True
    assert (
        mini_reserve.json()["workspace_invite_reserve"]["claim_supported_via_self_service"] is True
    )
