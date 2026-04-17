from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import PulseDigestIssue, utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    GroupWorkspaceInviteRole,
    GroupWorkspaceMemberRole,
    PaperType,
    PulseDigestIssueStatus,
    ResultShareKind,
    ResultShareViewAccessMode,
    ResultShareViewEventType,
    ResultShareViewOutcome,
)


def create_user(client, headers, *, email: str, name: str = "Overview User") -> dict:
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
            "identifiers": {"doi": f"10.1000/{title.lower().replace(' ', '-')}"},
            "source_links": [f"https://example.local/{title.lower().replace(' ', '-')}"],
            "last_touch_at": (utcnow() - timedelta(days=3)).isoformat(),
            "next_action": "Review latest result",
            "blocker": None,
            "priority": 4,
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


def add_workspace_member(client, headers, *, workspace_id: str, user_id: str, role: str) -> dict:
    response = client.post(
        f"/admin/group-workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": role},
    )
    assert response.status_code == 201
    return response.json()


def add_workspace_paper(client, headers, *, workspace_id: str, paper_id: str) -> dict:
    response = client.post(
        f"/admin/group-workspaces/{workspace_id}/papers",
        headers=headers,
        json={"paper_id": paper_id},
    )
    assert response.status_code == 201
    return response.json()


def create_result_share_grant(
    client,
    headers,
    *,
    share_kind: ResultShareKind,
    workspace_id: str | None = None,
    digest_issue_id: str | None = None,
    paper_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {"share_kind": share_kind.value}
    if workspace_id is not None:
        payload["workspace_id"] = workspace_id
    if digest_issue_id is not None:
        payload["digest_issue_id"] = digest_issue_id
    if paper_id is not None:
        payload["paper_id"] = paper_id
    response = client.post("/admin/result-share-grants", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def create_result_share_alias(client, headers, *, result_share_grant_id: str) -> dict:
    response = client.post(
        "/admin/result-share-aliases",
        headers=headers,
        json={"result_share_grant_id": result_share_grant_id},
    )
    assert response.status_code == 201
    return response.json()


def create_self_service_grant(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/subscription-self-service-grants",
        headers=headers,
        json={"user_id": user_id, "channel": ChannelType.OFFICIAL_ACCOUNT.value},
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


def create_digest_issue_with_single_paper(
    session, *, user_id: str, paper: dict, title: str
) -> dict:
    issue = PulseDigestIssue(
        user_id=UUID(user_id),
        issue_date=utcnow().date(),
        status=PulseDigestIssueStatus.PUBLISHED,
        title=title,
        summary=f"{title} summary",
        highlight_count=1,
        selected_card_count=1,
        content_payload={
            "sections": [
                {
                    "kind": "today_focus",
                    "title": "Today Focus",
                    "item_count": 1,
                    "items": [
                        {
                            "sort_order": 0,
                            "pulse_card_id": "00000000-0000-0000-0000-000000000010",
                            "card_type": "today_suggestion",
                            "source_paper_id": paper["id"],
                            "title": paper["title"],
                            "summary": "Digest item",
                            "paper": {
                                "id": paper["id"],
                                "user_id": user_id,
                                "title": paper["title"],
                                "type": paper["type"],
                                "stage": paper["stage"],
                                "venue": paper["venue"],
                                "priority": paper["priority"],
                                "next_action": paper["next_action"],
                                "blocker": paper["blocker"],
                                "last_touch_at": paper["last_touch_at"],
                                "progress_percentage": 100,
                            },
                        }
                    ],
                }
            ],
            "highlights": [],
            "items": [],
        },
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return {"id": str(issue.id), "title": issue.title}


def _override_conversion_settings():
    settings = get_settings()
    original = {
        "result_share_alias_enabled": settings.result_share_alias_enabled,
        "result_share_analytics_enabled": settings.result_share_analytics_enabled,
        "result_share_analytics_default_lookback_days": (
            settings.result_share_analytics_default_lookback_days
        ),
        "group_workspace_invites_enabled": settings.group_workspace_invites_enabled,
        "group_workspace_invite_web_entry_base_url": (
            settings.group_workspace_invite_web_entry_base_url
        ),
        "group_workspace_result_collect_enabled": settings.group_workspace_result_collect_enabled,
        "group_workspace_result_collect_allowed_share_kinds": (
            settings.group_workspace_result_collect_allowed_share_kinds
        ),
        "group_workspace_result_collect_allowed_roles": (
            settings.group_workspace_result_collect_allowed_roles
        ),
        "result_share_web_entry_base_url": settings.result_share_web_entry_base_url,
    }
    settings.result_share_alias_enabled = True
    settings.result_share_analytics_enabled = True
    settings.result_share_analytics_default_lookback_days = 30
    settings.group_workspace_invites_enabled = True
    settings.group_workspace_invite_web_entry_base_url = "http://127.0.0.1:5177/"
    settings.group_workspace_result_collect_enabled = True
    settings.group_workspace_result_collect_allowed_share_kinds = "digest_issue,paper_snapshot"
    settings.group_workspace_result_collect_allowed_roles = "owner,editor"
    settings.result_share_web_entry_base_url = "http://127.0.0.1:5174/"
    return settings, original


def _restore_conversion_settings(settings, original: dict) -> None:
    settings.result_share_alias_enabled = original["result_share_alias_enabled"]
    settings.result_share_analytics_enabled = original["result_share_analytics_enabled"]
    settings.result_share_analytics_default_lookback_days = original[
        "result_share_analytics_default_lookback_days"
    ]
    settings.group_workspace_invites_enabled = original["group_workspace_invites_enabled"]
    settings.group_workspace_invite_web_entry_base_url = original[
        "group_workspace_invite_web_entry_base_url"
    ]
    settings.group_workspace_result_collect_enabled = original[
        "group_workspace_result_collect_enabled"
    ]
    settings.group_workspace_result_collect_allowed_share_kinds = original[
        "group_workspace_result_collect_allowed_share_kinds"
    ]
    settings.group_workspace_result_collect_allowed_roles = original[
        "group_workspace_result_collect_allowed_roles"
    ]
    settings.result_share_web_entry_base_url = original["result_share_web_entry_base_url"]


def test_group_workspace_conversion_overview_aggregates_global_signals(
    client,
    operator_headers,
) -> None:
    settings, original = _override_conversion_settings()
    try:
        workspace = create_workspace(
            client,
            operator_headers,
            slug="conversion-global",
            name="Conversion Global",
        )
        board_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.WORKSPACE_BOARD,
            workspace_id=workspace["id"],
        )
        board_alias = create_result_share_alias(
            client,
            operator_headers,
            result_share_grant_id=board_share["grant"]["id"],
        )

        bootstrap = client.get(f"/result-shares/{board_share['plain_text_token']}/bootstrap")
        alias_content = client.get(f"/share-aliases/{board_alias['plain_text_alias']}/content")
        invite_redirect = client.get(
            f"/result-shares/{board_share['plain_text_token']}/invite-handoff",
            follow_redirects=False,
        )
        collect_redirect = client.get(
            f"/share-aliases/{board_alias['plain_text_alias']}/collect-handoff",
            follow_redirects=False,
        )
        assert bootstrap.status_code == 200
        assert alias_content.status_code == 200
        assert invite_redirect.status_code == 307
        assert collect_redirect.status_code == 307

        invite = create_invite_grant(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            role_to_assign=GroupWorkspaceInviteRole.VIEWER.value,
            max_claims=5,
        )
        claimed_user = create_user(
            client,
            operator_headers,
            email="conversion-claim@example.com",
            name="Conversion Claim",
        )
        claimed_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=claimed_user["id"],
        )
        claimed = client.post(
            f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
            headers={"Authorization": f"Bearer {claimed_grant['plain_text_token']}"},
        )
        assert claimed.status_code == 200
        assert claimed.json()["action"] == "claimed"

        already_member_user = create_user(
            client,
            operator_headers,
            email="conversion-member@example.com",
            name="Conversion Member",
        )
        add_workspace_member(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            user_id=already_member_user["id"],
            role=GroupWorkspaceMemberRole.VIEWER.value,
        )
        already_member_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=already_member_user["id"],
        )
        already_member = client.post(
            f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
            headers={"Authorization": f"Bearer {already_member_grant['plain_text_token']}"},
        )
        assert already_member.status_code == 200
        assert already_member.json()["action"] == "already_member"

        rejected_invite = create_invite_grant(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            role_to_assign=GroupWorkspaceInviteRole.VIEWER.value,
            max_claims=5,
        )
        revoke = client.post(
            f"/admin/group-workspace-invite-grants/{rejected_invite['grant']['id']}/revoke",
            headers=operator_headers,
        )
        assert revoke.status_code == 200
        rejected_user = create_user(
            client,
            operator_headers,
            email="conversion-rejected@example.com",
            name="Conversion Rejected",
        )
        rejected_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=rejected_user["id"],
        )
        rejected = client.post(
            f"/subscription-self-service/workspace-invites/{rejected_invite['plain_text_token']}/claim",
            headers={"Authorization": f"Bearer {rejected_grant['plain_text_token']}"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["action"] == "rejected"

        collector = create_user(
            client,
            operator_headers,
            email="conversion-collector@example.com",
            name="Conversion Collector",
        )
        add_workspace_member(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            user_id=collector["id"],
            role=GroupWorkspaceMemberRole.EDITOR.value,
        )
        paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Conversion Collect Paper",
        )
        paper_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.PAPER_SNAPSHOT,
            paper_id=paper["id"],
        )
        collector_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=collector["id"],
        )
        collect_headers = {"Authorization": f"Bearer {collector_grant['plain_text_token']}"}
        collected = client.post(
            f"/subscription-self-service/result-shares/{paper_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        already_present_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Conversion Already Present Paper",
        )
        add_workspace_paper(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            paper_id=already_present_paper["id"],
        )
        already_present_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.PAPER_SNAPSHOT,
            paper_id=already_present_paper["id"],
        )
        already_present_collect = client.post(
            f"/subscription-self-service/result-shares/{already_present_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        assert collected.status_code == 200
        assert collected.json()["action"] == "collected"
        assert already_present_collect.status_code == 200
        assert already_present_collect.json()["action"] == "already_present"

        overview = client.get(
            "/admin/group-workspace-conversion-overview",
            headers=operator_headers,
        )
        assert overview.status_code == 200
        payload = overview.json()
        assert payload["total_share_view_events"] == 4
        assert payload["bootstrap_view_count"] == 1
        assert payload["content_view_count"] == 1
        assert payload["redirect_count"] == 0
        assert payload["invite_handoff_redirect_count"] == 1
        assert payload["collect_handoff_redirect_count"] == 1
        assert payload["resolved_event_count"] == 4
        assert payload["rejected_event_count"] == 0
        assert payload["by_share_kind"] == {"workspace_board": 4}
        assert payload["by_access_mode"] == {"share_token": 2, "alias": 2}
        assert payload["by_handoff_target"] == {
            "group_workspace_invite_entry": 1,
            "result_share_collect_entry": 1,
        }
        assert payload["invite_claimed_count"] == 1
        assert payload["invite_already_member_count"] == 1
        assert payload["invite_rejected_count"] == 1
        assert payload["collect_collected_count"] == 1
        assert payload["collect_already_present_count"] == 1
        assert payload["collect_rejected_count"] == 0
        assert payload["unique_result_share_grant_count"] == 3
        assert payload["unique_workspace_count"] == 1
        assert payload["last_activity_at"] is not None
        assert (
            "invite_claimed_count"
            in payload["attribution_scope"]["workspace_level_aggregate_metrics"]
        )
        assert (
            "total_share_view_events" in payload["attribution_scope"]["direct_attribution_metrics"]
        )
        assert "Collect metrics are directly linked" in " ".join(
            payload["attribution_scope"]["notes"]
        )

        filtered_overview = client.get(
            "/admin/group-workspace-conversion-overview",
            headers=operator_headers,
            params={
                "share_kind": ResultShareKind.WORKSPACE_BOARD.value,
                "access_mode": ResultShareViewAccessMode.ALIAS.value,
                "event_type": ResultShareViewEventType.CONTENT_VIEW.value,
                "outcome": ResultShareViewOutcome.RESOLVED.value,
            },
        )
        assert filtered_overview.status_code == 200
        filtered_payload = filtered_overview.json()
        assert filtered_payload["total_share_view_events"] == 1
        assert filtered_payload["bootstrap_view_count"] == 0
        assert filtered_payload["content_view_count"] == 1
        assert filtered_payload["redirect_count"] == 0
        assert filtered_payload["invite_handoff_redirect_count"] == 0
        assert filtered_payload["collect_handoff_redirect_count"] == 0
        assert filtered_payload["resolved_event_count"] == 1
        assert filtered_payload["rejected_event_count"] == 0
        assert filtered_payload["by_share_kind"] == {"workspace_board": 1}
        assert filtered_payload["by_access_mode"] == {"alias": 1}
        assert filtered_payload["by_handoff_target"] == {}
        assert filtered_payload["invite_claimed_count"] == 1
        assert filtered_payload["invite_already_member_count"] == 1
        assert filtered_payload["invite_rejected_count"] == 1
        assert filtered_payload["collect_collected_count"] == 0
        assert filtered_payload["collect_already_present_count"] == 0
        assert filtered_payload["collect_rejected_count"] == 0
        assert filtered_payload["unique_result_share_grant_count"] == 1
        assert filtered_payload["unique_workspace_count"] == 1
        assert "share_kind filters scope view-event metrics" in " ".join(
            filtered_payload["attribution_scope"]["notes"]
        )
        assert "access_mode and event_type filters scope only" in " ".join(
            filtered_payload["attribution_scope"]["notes"]
        )

        serialized = json.dumps(payload)
        assert board_share["plain_text_token"] not in serialized
        assert board_alias["plain_text_alias"] not in serialized
        assert paper_share["plain_text_token"] not in serialized
        assert "/Users/" not in serialized
    finally:
        _restore_conversion_settings(settings, original)


def test_group_workspace_workspace_conversion_overview_aggregates_workspace_signals(
    client,
    operator_headers,
    session,
) -> None:
    settings, original = _override_conversion_settings()
    try:
        workspace = create_workspace(
            client,
            operator_headers,
            slug="conversion-workspace",
            name="Conversion Workspace",
        )
        board_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.WORKSPACE_BOARD,
            workspace_id=workspace["id"],
        )
        board_alias = create_result_share_alias(
            client,
            operator_headers,
            result_share_grant_id=board_share["grant"]["id"],
        )
        assert (
            client.get(f"/result-shares/{board_share['plain_text_token']}/bootstrap").status_code
            == 200
        )
        assert (
            client.get(f"/share-aliases/{board_alias['plain_text_alias']}/content").status_code
            == 200
        )
        assert (
            client.get(
                f"/result-shares/{board_share['plain_text_token']}/invite-handoff",
                follow_redirects=False,
            ).status_code
            == 307
        )
        assert (
            client.get(
                f"/share-aliases/{board_alias['plain_text_alias']}/collect-handoff",
                follow_redirects=False,
            ).status_code
            == 307
        )

        invite = create_invite_grant(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            role_to_assign=GroupWorkspaceInviteRole.VIEWER.value,
            max_claims=5,
        )
        claimed_user = create_user(
            client,
            operator_headers,
            email="workspace-claim@example.com",
            name="Workspace Claim",
        )
        claimed_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=claimed_user["id"],
        )
        claimed = client.post(
            f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
            headers={"Authorization": f"Bearer {claimed_grant['plain_text_token']}"},
        )
        assert claimed.status_code == 200
        assert claimed.json()["action"] == "claimed"

        member_user = create_user(
            client,
            operator_headers,
            email="workspace-member@example.com",
            name="Workspace Member",
        )
        add_workspace_member(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            user_id=member_user["id"],
            role=GroupWorkspaceMemberRole.VIEWER.value,
        )
        member_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=member_user["id"],
        )
        already_member = client.post(
            f"/subscription-self-service/workspace-invites/{invite['plain_text_token']}/claim",
            headers={"Authorization": f"Bearer {member_grant['plain_text_token']}"},
        )
        assert already_member.status_code == 200
        assert already_member.json()["action"] == "already_member"

        collector = create_user(
            client,
            operator_headers,
            email="workspace-collector@example.com",
            name="Workspace Collector",
        )
        add_workspace_member(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            user_id=collector["id"],
            role=GroupWorkspaceMemberRole.OWNER.value,
        )
        paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Workspace Paper Share",
        )
        digest_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Workspace Digest Share",
        )
        digest_issue = create_digest_issue_with_single_paper(
            session,
            user_id=collector["id"],
            paper=digest_paper,
            title="Workspace Digest Issue",
        )
        paper_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.PAPER_SNAPSHOT,
            paper_id=paper["id"],
        )
        digest_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.DIGEST_ISSUE,
            digest_issue_id=digest_issue["id"],
        )
        collector_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=collector["id"],
        )
        collect_headers = {"Authorization": f"Bearer {collector_grant['plain_text_token']}"}
        paper_collect = client.post(
            f"/subscription-self-service/result-shares/{paper_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        paper_repeat = client.post(
            f"/subscription-self-service/result-shares/{paper_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        already_present_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Workspace Already Present Share",
        )
        add_workspace_paper(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            paper_id=already_present_paper["id"],
        )
        already_present_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.PAPER_SNAPSHOT,
            paper_id=already_present_paper["id"],
        )
        already_present_collect = client.post(
            f"/subscription-self-service/result-shares/{already_present_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        digest_collect = client.post(
            f"/subscription-self-service/result-shares/{digest_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        assert paper_collect.status_code == 200
        assert paper_collect.json()["action"] == "collected"
        assert paper_repeat.status_code == 200
        assert paper_repeat.json()["action"] == "already_present"
        assert already_present_collect.status_code == 200
        assert already_present_collect.json()["action"] == "already_present"
        assert digest_collect.status_code == 200
        assert digest_collect.json()["action"] == "collected"

        overview = client.get(
            f"/admin/group-workspaces/{workspace['id']}/conversion-overview",
            headers=operator_headers,
        )
        assert overview.status_code == 200
        payload = overview.json()
        assert payload["workspace"]["id"] == workspace["id"]
        assert payload["active_workspace_board_share_grant_count"] == 1
        assert payload["active_digest_issue_share_grant_count"] == 1
        assert payload["active_paper_snapshot_share_grant_count"] == 2
        assert payload["active_invite_grant_count"] == 1
        assert payload["workspace_board_view_count"] == 2
        assert payload["invite_handoff_redirect_count"] == 1
        assert payload["collect_handoff_redirect_count"] == 1
        assert payload["invite_claimed_count"] == 1
        assert payload["invite_already_member_count"] == 1
        assert payload["collect_collected_count"] == 2
        assert payload["collect_already_present_count"] == 1
        assert payload["unique_collected_paper_count"] == 3
        assert payload["unique_collecting_user_count"] == 1
        assert payload["last_activity_at"] is not None
        assert (
            "workspace_board_view_count"
            in payload["attribution_scope"]["direct_attribution_metrics"]
        )
        assert (
            "unique_collecting_user_count"
            in payload["attribution_scope"]["workspace_level_aggregate_metrics"]
        )

        filtered_overview = client.get(
            f"/admin/group-workspaces/{workspace['id']}/conversion-overview",
            headers=operator_headers,
            params={
                "share_kind": ResultShareKind.WORKSPACE_BOARD.value,
                "access_mode": ResultShareViewAccessMode.ALIAS.value,
                "event_type": ResultShareViewEventType.CONTENT_VIEW.value,
                "outcome": ResultShareViewOutcome.RESOLVED.value,
            },
        )
        assert filtered_overview.status_code == 200
        filtered_payload = filtered_overview.json()
        assert filtered_payload["workspace"]["id"] == workspace["id"]
        assert filtered_payload["active_workspace_board_share_grant_count"] == 1
        assert filtered_payload["active_digest_issue_share_grant_count"] == 0
        assert filtered_payload["active_paper_snapshot_share_grant_count"] == 0
        assert filtered_payload["active_invite_grant_count"] == 1
        assert filtered_payload["workspace_board_view_count"] == 1
        assert filtered_payload["invite_handoff_redirect_count"] == 0
        assert filtered_payload["collect_handoff_redirect_count"] == 0
        assert filtered_payload["invite_claimed_count"] == 1
        assert filtered_payload["invite_already_member_count"] == 1
        assert filtered_payload["collect_collected_count"] == 0
        assert filtered_payload["collect_already_present_count"] == 0
        assert filtered_payload["unique_collected_paper_count"] == 0
        assert filtered_payload["unique_collecting_user_count"] == 0
        assert "share_kind filters scope view-event metrics" in " ".join(
            filtered_payload["attribution_scope"]["notes"]
        )
        assert "access_mode and event_type filters scope only" in " ".join(
            filtered_payload["attribution_scope"]["notes"]
        )

        serialized = json.dumps(payload)
        assert board_share["plain_text_token"] not in serialized
        assert board_alias["plain_text_alias"] not in serialized
        assert paper_share["plain_text_token"] not in serialized
        assert digest_share["plain_text_token"] not in serialized
        assert "/Users/" not in serialized
    finally:
        _restore_conversion_settings(settings, original)
