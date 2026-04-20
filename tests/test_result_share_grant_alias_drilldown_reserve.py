from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import (
    GroupWorkspaceResultCollectRecord,
    PulseDigestIssue,
    ResultShareViewEvent,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ChannelType,
    GroupWorkspaceMemberRole,
    GroupWorkspaceResultCollectStatus,
    PaperType,
    PulseDigestIssueStatus,
    ResultShareKind,
    ResultShareViewAccessMode,
    ResultShareViewEventType,
)


def create_user(client, headers, *, email: str, name: str) -> dict:
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
            "last_touch_at": (utcnow() - timedelta(days=2)).isoformat(),
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


def create_digest_issue_with_papers(
    session,
    *,
    user_id: str,
    papers: list[dict],
    title: str,
) -> dict:
    items = []
    for index, paper in enumerate(papers):
        items.append(
            {
                "sort_order": index,
                "pulse_card_id": f"00000000-0000-0000-0000-0000000001{index:02d}",
                "card_type": "today_suggestion",
                "source_paper_id": paper["id"],
                "title": paper["title"],
                "summary": f"{paper['title']} summary",
                "paper": {
                    "paper_id": paper["id"],
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
        )
    issue = PulseDigestIssue(
        user_id=UUID(user_id),
        issue_date=utcnow().date(),
        status=PulseDigestIssueStatus.PUBLISHED,
        title=title,
        summary=f"{title} summary",
        highlight_count=len(items),
        selected_card_count=len(items),
        content_payload={
            "sections": [
                {
                    "kind": "today_focus",
                    "title": "Today Focus",
                    "item_count": len(items),
                    "items": items,
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


def add_manual_rejected_collect_record(
    session,
    *,
    workspace_id: str,
    user_id: str,
    grant_id: str,
    digest_issue_id: str,
    collected_paper_id: str,
    created_at,
) -> None:
    record = GroupWorkspaceResultCollectRecord(
        workspace_id=UUID(workspace_id),
        user_id=UUID(user_id),
        result_share_grant_id=UUID(grant_id),
        share_kind=ResultShareKind.DIGEST_ISSUE,
        digest_issue_id=UUID(digest_issue_id),
        source_pulse_card_id=None,
        source_paper_id=UUID(collected_paper_id),
        collected_paper_id=UUID(collected_paper_id),
        idempotency_key=f"manual-rejected:{grant_id}:{user_id}:{collected_paper_id}",
        status=GroupWorkspaceResultCollectStatus.REJECTED,
        reason_codes=["manual_reject_test"],
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(record)
    session.commit()


def age_share_event(
    session,
    *,
    grant_id: str,
    alias_id: str | None,
    access_mode: ResultShareViewAccessMode,
    event_type: ResultShareViewEventType,
    days: int,
) -> None:
    statement = (
        select(ResultShareViewEvent)
        .where(
            ResultShareViewEvent.result_share_grant_id == UUID(grant_id),
            ResultShareViewEvent.access_mode == access_mode,
            ResultShareViewEvent.event_type == event_type,
        )
        .limit(1)
    )
    if alias_id is None:
        statement = statement.where(ResultShareViewEvent.result_share_alias_id.is_(None))
    else:
        statement = statement.where(ResultShareViewEvent.result_share_alias_id == UUID(alias_id))
    event = session.scalar(statement)
    assert event is not None
    older = utcnow() - timedelta(days=days)
    event.occurred_at = older
    event.created_at = older
    session.commit()


def _override_settings():
    settings = get_settings()
    original = {
        "result_share_alias_enabled": settings.result_share_alias_enabled,
        "result_share_redirect_enabled": settings.result_share_redirect_enabled,
        "result_share_web_entry_base_url": settings.result_share_web_entry_base_url,
        "result_share_analytics_enabled": settings.result_share_analytics_enabled,
        "result_share_analytics_default_lookback_days": (
            settings.result_share_analytics_default_lookback_days
        ),
        "group_workspace_result_collect_enabled": settings.group_workspace_result_collect_enabled,
        "group_workspace_result_collect_allowed_share_kinds": (
            settings.group_workspace_result_collect_allowed_share_kinds
        ),
        "group_workspace_result_collect_allowed_roles": (
            settings.group_workspace_result_collect_allowed_roles
        ),
    }
    settings.result_share_alias_enabled = True
    settings.result_share_redirect_enabled = True
    settings.result_share_web_entry_base_url = "http://127.0.0.1:5174/"
    settings.result_share_analytics_enabled = True
    settings.result_share_analytics_default_lookback_days = 30
    settings.group_workspace_result_collect_enabled = True
    settings.group_workspace_result_collect_allowed_share_kinds = "digest_issue,paper_snapshot"
    settings.group_workspace_result_collect_allowed_roles = "owner,editor"
    return settings, original


def _restore_settings(settings, original: dict) -> None:
    settings.result_share_alias_enabled = original["result_share_alias_enabled"]
    settings.result_share_redirect_enabled = original["result_share_redirect_enabled"]
    settings.result_share_web_entry_base_url = original["result_share_web_entry_base_url"]
    settings.result_share_analytics_enabled = original["result_share_analytics_enabled"]
    settings.result_share_analytics_default_lookback_days = original[
        "result_share_analytics_default_lookback_days"
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


def test_result_share_grant_conversion_drilldown_returns_direct_event_and_collect_breakdown(
    client,
    operator_headers,
    session,
) -> None:
    settings, original = _override_settings()
    try:
        collector = create_user(
            client,
            operator_headers,
            email="grant-drilldown-collector@example.com",
            name="Grant Drilldown Collector",
        )
        rejected_user = create_user(
            client,
            operator_headers,
            email="grant-drilldown-rejected@example.com",
            name="Grant Drilldown Rejected",
        )
        digest_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Grant Drilldown Digest Paper",
        )
        already_present_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Grant Drilldown Already Present",
        )
        rejected_paper = create_paper(
            client,
            operator_headers,
            user_id=rejected_user["id"],
            title="Grant Drilldown Rejected Paper",
        )
        digest_issue = create_digest_issue_with_papers(
            session,
            user_id=collector["id"],
            papers=[digest_paper, already_present_paper],
            title="Grant Drilldown Digest",
        )
        workspace = create_workspace(
            client,
            operator_headers,
            slug="grant-drilldown-workspace",
            name="Grant Drilldown Workspace",
        )
        add_workspace_member(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            user_id=collector["id"],
            role=GroupWorkspaceMemberRole.OWNER.value,
        )
        add_workspace_paper(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            paper_id=already_present_paper["id"],
        )

        share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.DIGEST_ISSUE,
            digest_issue_id=digest_issue["id"],
        )
        active_alias = create_result_share_alias(
            client,
            operator_headers,
            result_share_grant_id=share["grant"]["id"],
        )
        revoked_alias = create_result_share_alias(
            client,
            operator_headers,
            result_share_grant_id=share["grant"]["id"],
        )

        bootstrap = client.get(f"/result-shares/{share['plain_text_token']}/bootstrap")
        content = client.get(f"/result-shares/{share['plain_text_token']}/content")
        alias_bootstrap = client.get(f"/share-aliases/{active_alias['plain_text_alias']}/bootstrap")
        alias_content = client.get(f"/share-aliases/{active_alias['plain_text_alias']}/content")
        assert bootstrap.status_code == 200
        assert content.status_code == 200
        assert alias_bootstrap.status_code == 200
        assert alias_content.status_code == 200
        redirect = client.get(
            f"/s/{active_alias['plain_text_alias']}",
            follow_redirects=False,
        )
        assert redirect.status_code == 307

        revoke_alias = client.post(
            f"/admin/result-share-aliases/{revoked_alias['alias']['id']}/revoke",
            headers=operator_headers,
        )
        assert revoke_alias.status_code == 200
        rejected_alias_bootstrap = client.get(
            f"/share-aliases/{revoked_alias['plain_text_alias']}/bootstrap"
        )
        assert rejected_alias_bootstrap.status_code == 401

        collector_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=collector["id"],
        )
        collect = client.post(
            f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
            headers={"Authorization": f"Bearer {collector_grant['plain_text_token']}"},
            json={
                "workspace_id": workspace["id"],
                "paper_ids": [digest_paper["id"], already_present_paper["id"]],
            },
        )
        assert collect.status_code == 200
        assert collect.json()["action"] == "collected"

        old_timestamp = utcnow() - timedelta(days=20)
        add_manual_rejected_collect_record(
            session,
            workspace_id=workspace["id"],
            user_id=rejected_user["id"],
            grant_id=share["grant"]["id"],
            digest_issue_id=digest_issue["id"],
            collected_paper_id=rejected_paper["id"],
            created_at=old_timestamp,
        )
        age_share_event(
            session,
            grant_id=share["grant"]["id"],
            alias_id=None,
            access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
            event_type=ResultShareViewEventType.BOOTSTRAP_VIEW,
            days=20,
        )

        drilldown = client.get(
            f"/admin/result-share-grants/{share['grant']['id']}/conversion-drilldown",
            headers=operator_headers,
        )
        assert drilldown.status_code == 200
        payload = drilldown.json()

        assert payload["share_grant"]["grant_id"] == share["grant"]["id"]
        assert payload["share_grant"]["share_kind"] == "digest_issue"
        assert payload["window_start"] is not None
        assert payload["total_events"] == 6
        assert payload["bootstrap_view_count"] == 3
        assert payload["content_view_count"] == 2
        assert payload["redirect_count"] == 1
        assert payload["invite_handoff_redirect_count"] == 0
        assert payload["collect_handoff_redirect_count"] == 0
        assert payload["resolved_event_count"] == 5
        assert payload["rejected_event_count"] == 1
        assert payload["by_access_mode"] == {
            "share_token": 2,
            "alias": 3,
            "alias_redirect": 1,
        }
        assert payload["by_event_type"] == {
            "bootstrap_view": 3,
            "content_view": 2,
            "redirect": 1,
        }
        assert payload["by_outcome"] == {"resolved": 5, "rejected": 1}
        assert payload["active_alias_count"] == 1
        assert {alias["status"] for alias in payload["aliases"]} == {"active", "revoked"}
        assert payload["direct_collect_collected_count"] == 1
        assert payload["direct_collect_already_present_count"] == 1
        assert payload["direct_collect_rejected_count"] == 1
        assert payload["unique_collecting_user_count"] == 2
        assert len(payload["recent_events"]) == 6
        assert len(payload["direct_collect_records"]) == 3
        assert {record["status"] for record in payload["direct_collect_records"]} == {
            "collected",
            "already_present",
            "rejected",
        }
        assert "direct_collect_records" in payload["attribution_scope"]["direct_collect_metrics"]
        assert "share_grant" in payload["attribution_scope"]["non_attribution_fields"]
        assert any("plaintext aliases" in note for note in payload["notes"])
        assert "referrer_host" not in payload["recent_events"][0]
        assert "user_agent_family" not in payload["recent_events"][0]

        filtered = client.get(
            f"/admin/result-share-grants/{share['grant']['id']}/conversion-drilldown",
            headers=operator_headers,
            params={
                "date_from": (utcnow() - timedelta(days=7)).isoformat(),
                "access_mode": "alias",
                "event_type": "content_view",
                "outcome": "resolved",
                "limit": 2,
            },
        )
        assert filtered.status_code == 200
        filtered_payload = filtered.json()
        assert filtered_payload["total_events"] == 1
        assert filtered_payload["bootstrap_view_count"] == 0
        assert filtered_payload["content_view_count"] == 1
        assert filtered_payload["redirect_count"] == 0
        assert filtered_payload["resolved_event_count"] == 1
        assert filtered_payload["rejected_event_count"] == 0
        assert filtered_payload["by_access_mode"] == {"alias": 1}
        assert filtered_payload["by_event_type"] == {"content_view": 1}
        assert filtered_payload["by_outcome"] == {"resolved": 1}
        assert len(filtered_payload["recent_events"]) == 1
        assert filtered_payload["direct_collect_collected_count"] == 1
        assert filtered_payload["direct_collect_already_present_count"] == 1
        assert filtered_payload["direct_collect_rejected_count"] == 0
        assert len(filtered_payload["direct_collect_records"]) == 2

        serialized = json.dumps(payload)
        assert share["plain_text_token"] not in serialized
        assert active_alias["plain_text_alias"] not in serialized
        assert revoked_alias["plain_text_alias"] not in serialized
        assert "/Users/" not in serialized
    finally:
        _restore_settings(settings, original)


def test_result_share_alias_conversion_drilldown_is_alias_scoped_and_does_not_claim_collects(
    client,
    operator_headers,
    session,
) -> None:
    settings, original = _override_settings()
    try:
        collector = create_user(
            client,
            operator_headers,
            email="alias-drilldown-collector@example.com",
            name="Alias Drilldown Collector",
        )
        digest_paper = create_paper(
            client,
            operator_headers,
            user_id=collector["id"],
            title="Alias Drilldown Digest Paper",
        )
        digest_issue = create_digest_issue_with_papers(
            session,
            user_id=collector["id"],
            papers=[digest_paper],
            title="Alias Drilldown Digest",
        )
        workspace = create_workspace(
            client,
            operator_headers,
            slug="alias-drilldown-workspace",
            name="Alias Drilldown Workspace",
        )
        add_workspace_member(
            client,
            operator_headers,
            workspace_id=workspace["id"],
            user_id=collector["id"],
            role=GroupWorkspaceMemberRole.EDITOR.value,
        )

        share = create_result_share_grant(
            client,
            operator_headers,
            share_kind=ResultShareKind.DIGEST_ISSUE,
            digest_issue_id=digest_issue["id"],
        )
        alias_a = create_result_share_alias(
            client,
            operator_headers,
            result_share_grant_id=share["grant"]["id"],
        )
        alias_b = create_result_share_alias(
            client,
            operator_headers,
            result_share_grant_id=share["grant"]["id"],
        )

        alias_a_bootstrap = client.get(f"/share-aliases/{alias_a['plain_text_alias']}/bootstrap")
        alias_a_content = client.get(f"/share-aliases/{alias_a['plain_text_alias']}/content")
        redirect = client.get(
            f"/s/{alias_a['plain_text_alias']}",
            follow_redirects=False,
        )
        alias_b_bootstrap = client.get(f"/share-aliases/{alias_b['plain_text_alias']}/bootstrap")
        assert alias_a_bootstrap.status_code == 200
        assert alias_a_content.status_code == 200
        assert redirect.status_code == 307
        assert alias_b_bootstrap.status_code == 200

        collector_grant = create_self_service_grant(
            client,
            operator_headers,
            user_id=collector["id"],
        )
        collect = client.post(
            f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
            headers={"Authorization": f"Bearer {collector_grant['plain_text_token']}"},
            json={"workspace_id": workspace["id"], "paper_ids": [digest_paper["id"]]},
        )
        assert collect.status_code == 200

        drilldown = client.get(
            f"/admin/result-share-aliases/{alias_a['alias']['id']}/conversion-drilldown",
            headers=operator_headers,
        )
        assert drilldown.status_code == 200
        payload = drilldown.json()

        assert payload["alias"]["alias_id"] == alias_a["alias"]["id"]
        assert payload["result_share_grant"]["grant_id"] == share["grant"]["id"]
        assert payload["window_start"] is not None
        assert payload["total_events"] == 3
        assert payload["bootstrap_view_count"] == 1
        assert payload["content_view_count"] == 1
        assert payload["redirect_count"] == 1
        assert payload["invite_handoff_redirect_count"] == 0
        assert payload["collect_handoff_redirect_count"] == 0
        assert payload["resolved_event_count"] == 3
        assert payload["rejected_event_count"] == 0
        assert payload["by_event_type"] == {
            "bootstrap_view": 1,
            "content_view": 1,
            "redirect": 1,
        }
        assert payload["by_outcome"] == {"resolved": 3}
        assert len(payload["recent_events"]) == 3
        assert {event["result_share_alias_id"] for event in payload["recent_events"]} == {
            alias_a["alias"]["id"]
        }
        assert payload["attribution_scope"]["direct_collect_metrics"] == []
        assert "result_share_grant" in payload["attribution_scope"]["non_attribution_fields"]
        assert any("grant-level" in note for note in payload["notes"])
        assert "direct_collect_records" not in payload

        filtered = client.get(
            f"/admin/result-share-aliases/{alias_a['alias']['id']}/conversion-drilldown",
            headers=operator_headers,
            params={
                "event_type": "content_view",
                "outcome": "resolved",
                "limit": 1,
            },
        )
        assert filtered.status_code == 200
        filtered_payload = filtered.json()
        assert filtered_payload["total_events"] == 1
        assert filtered_payload["bootstrap_view_count"] == 0
        assert filtered_payload["content_view_count"] == 1
        assert filtered_payload["redirect_count"] == 0
        assert filtered_payload["by_event_type"] == {"content_view": 1}
        assert filtered_payload["by_outcome"] == {"resolved": 1}
        assert len(filtered_payload["recent_events"]) == 1
        assert (
            filtered_payload["recent_events"][0]["result_share_alias_id"] == alias_a["alias"]["id"]
        )

        serialized = json.dumps(payload)
        assert share["plain_text_token"] not in serialized
        assert alias_a["plain_text_alias"] not in serialized
        assert alias_b["plain_text_alias"] not in serialized
        assert "/Users/" not in serialized
    finally:
        _restore_settings(settings, original)
