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
)


def create_user(client, headers, *, email: str, name: str = "Drilldown User") -> dict:
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


def test_group_workspace_conversion_drilldown_returns_global_buckets_and_recent_lists(
    client,
    operator_headers,
) -> None:
    settings, original = _override_conversion_settings()
    try:
        workspace = create_workspace(
            client,
            operator_headers,
            slug="drilldown-global",
            name="Drilldown Global",
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
        assert bootstrap.status_code == 200
        assert alias_content.status_code == 200
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
            email="drilldown-global-claim@example.com",
            name="Drilldown Claim",
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
            email="drilldown-global-member@example.com",
            name="Drilldown Member",
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
            email="drilldown-global-collector@example.com",
            name="Drilldown Collector",
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
            title="Drilldown Collect Paper",
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
            title="Drilldown Already Present Paper",
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
        already_present = client.post(
            f"/subscription-self-service/result-shares/{already_present_share['plain_text_token']}/collect",
            headers=collect_headers,
            json={"workspace_id": workspace["id"]},
        )
        assert collected.status_code == 200
        assert collected.json()["action"] == "collected"
        assert already_present.status_code == 200
        assert already_present.json()["action"] == "already_present"

        secondary_workspace = create_workspace(
            client,
            operator_headers,
            slug="drilldown-secondary",
            name="Drilldown Secondary",
        )
        secondary_board_share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.WORKSPACE_BOARD,
            workspace_id=secondary_workspace["id"],
        )
        assert (
            client.get(
                f"/result-shares/{secondary_board_share['plain_text_token']}/bootstrap"
            ).status_code
            == 200
        )

        drilldown = client.get(
            "/admin/group-workspace-conversion-drilldown?limit=5",
            headers=operator_headers,
        )
        assert drilldown.status_code == 200
        payload = drilldown.json()

        assert payload["window_start"] is not None
        assert payload["daily_buckets"][0]["share_view_count"] == 3
        assert payload["daily_buckets"][0]["invite_handoff_redirect_count"] == 1
        assert payload["daily_buckets"][0]["collect_handoff_redirect_count"] == 1
        assert payload["daily_buckets"][0]["invite_claimed_count"] == 1
        assert payload["daily_buckets"][0]["invite_already_member_count"] == 1
        assert payload["daily_buckets"][0]["collect_collected_count"] == 1
        assert payload["daily_buckets"][0]["collect_already_present_count"] == 1

        assert payload["top_workspaces"][0]["workspace"]["id"] == workspace["id"]
        assert payload["top_workspaces"][0]["workspace_board_view_count"] == 2
        assert payload["top_workspaces"][0]["invite_handoff_redirect_count"] == 1
        assert payload["top_workspaces"][0]["collect_handoff_redirect_count"] == 1
        assert payload["top_workspaces"][0]["invite_claimed_count"] == 1
        assert payload["top_workspaces"][0]["collect_collected_count"] == 1

        assert (
            payload["top_result_share_grants"][0]["result_share_grant_id"]
            == board_share["grant"]["id"]
        )
        assert payload["top_result_share_grants"][0]["bootstrap_view_count"] == 1
        assert payload["top_result_share_grants"][0]["content_view_count"] == 1
        assert payload["top_result_share_grants"][0]["invite_handoff_redirect_count"] == 1
        assert payload["top_result_share_grants"][0]["collect_handoff_redirect_count"] == 1
        assert paper_share["grant"]["id"] in {
            row["result_share_grant_id"] for row in payload["top_result_share_grants"]
        }

        assert len(payload["recent_share_events"]) == 5
        assert {event["event_type"] for event in payload["recent_share_events"]} == {
            "bootstrap_view",
            "content_view",
            "invite_handoff_redirect",
            "collect_handoff_redirect",
        }
        assert len(payload["recent_invite_claims"]) == 2
        assert {claim["claim_status"] for claim in payload["recent_invite_claims"]} == {
            "claimed",
            "already_member",
        }
        assert len(payload["recent_collect_records"]) == 2
        assert {record["status"] for record in payload["recent_collect_records"]} == {
            "collected",
            "already_present",
        }

        assert (
            "total_share_view_events" in payload["attribution_scope"]["direct_attribution_metrics"]
        )
        assert (
            "invite_claimed_count"
            in payload["attribution_scope"]["workspace_level_aggregate_metrics"]
        )
        assert any(
            "Daily buckets count bootstrap/content share views" in note for note in payload["notes"]
        )
        assert any(
            "Top result-share grants include only records" in note for note in payload["notes"]
        )
        assert "referrer_host" not in payload["recent_share_events"][0]
        assert "user_agent_family" not in payload["recent_share_events"][0]

        serialized = json.dumps(payload)
        assert board_share["plain_text_token"] not in serialized
        assert board_alias["plain_text_alias"] not in serialized
        assert paper_share["plain_text_token"] not in serialized
        assert secondary_board_share["plain_text_token"] not in serialized
        assert "/Users/" not in serialized
    finally:
        _restore_conversion_settings(settings, original)


def test_group_workspace_conversion_drilldown_returns_workspace_scoped_recent_activity(
    client,
    operator_headers,
    session,
) -> None:
    settings, original = _override_conversion_settings()
    try:
        workspace = create_workspace(
            client,
            operator_headers,
            slug="drilldown-workspace",
            name="Drilldown Workspace",
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
        assert bootstrap.status_code == 200
        assert alias_content.status_code == 200
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
            email="drilldown-workspace-claim@example.com",
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
            email="drilldown-workspace-member@example.com",
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
            email="drilldown-workspace-collector@example.com",
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
            title="Workspace Drilldown Paper",
        )
        digest_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Workspace Drilldown Digest Paper",
        )
        digest_issue = create_digest_issue_with_single_paper(
            session,
            user_id=collector["id"],
            paper=digest_paper,
            title="Workspace Drilldown Digest Issue",
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
        already_present_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Workspace Drilldown Already Present",
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
        assert already_present_collect.status_code == 200
        assert already_present_collect.json()["action"] == "already_present"
        assert digest_collect.status_code == 200
        assert digest_collect.json()["action"] == "collected"

        drilldown = client.get(
            f"/admin/group-workspaces/{workspace['id']}/conversion-drilldown?limit=10",
            headers=operator_headers,
        )
        assert drilldown.status_code == 200
        payload = drilldown.json()

        assert payload["workspace"]["id"] == workspace["id"]
        assert payload["daily_buckets"][0]["share_view_count"] == 2
        assert payload["daily_buckets"][0]["invite_handoff_redirect_count"] == 1
        assert payload["daily_buckets"][0]["collect_handoff_redirect_count"] == 1
        assert payload["daily_buckets"][0]["invite_claimed_count"] == 1
        assert payload["daily_buckets"][0]["invite_already_member_count"] == 1
        assert payload["daily_buckets"][0]["collect_collected_count"] == 2
        assert payload["daily_buckets"][0]["collect_already_present_count"] == 1

        assert payload["active_share_grant_snapshot"] == {
            "active_workspace_board_share_grant_count": 1,
            "active_digest_issue_share_grant_count": 1,
            "active_paper_snapshot_share_grant_count": 2,
        }
        assert payload["active_invite_grant_snapshot"] == {"active_invite_grant_count": 1}

        assert len(payload["recent_share_events"]) == 4
        assert {event["event_type"] for event in payload["recent_share_events"]} == {
            "bootstrap_view",
            "content_view",
            "invite_handoff_redirect",
            "collect_handoff_redirect",
        }
        assert len(payload["recent_invite_claims"]) == 2
        assert {claim["claim_status"] for claim in payload["recent_invite_claims"]} == {
            "claimed",
            "already_member",
        }
        assert len(payload["recent_collect_records"]) == 3
        assert {record["status"] for record in payload["recent_collect_records"]} == {
            "collected",
            "already_present",
        }

        assert (
            "workspace_board_view_count"
            in payload["attribution_scope"]["direct_attribution_metrics"]
        )
        assert (
            "invite_claimed_count"
            in payload["attribution_scope"]["workspace_level_aggregate_metrics"]
        )
        assert any(
            "Active share-grant and invite-grant snapshots describe current workspace inventory"
            in note
            for note in payload["notes"]
        )
        assert "referrer_host" not in payload["recent_share_events"][0]
        assert "user_agent_family" not in payload["recent_share_events"][0]

        serialized = json.dumps(payload)
        assert board_share["plain_text_token"] not in serialized
        assert board_alias["plain_text_alias"] not in serialized
        assert paper_share["plain_text_token"] not in serialized
        assert digest_share["plain_text_token"] not in serialized
        assert already_present_share["plain_text_token"] not in serialized
        assert "/Users/" not in serialized
    finally:
        _restore_conversion_settings(settings, original)
