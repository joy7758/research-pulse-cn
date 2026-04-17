from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import PulseDigestIssue, utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    GroupWorkspaceMemberRole,
    MiniReadGrantType,
    PaperType,
    PulseDigestIssueStatus,
    ResultShareKind,
)


def enable_result_collect(
    monkeypatch,
    *,
    enabled: bool = True,
    share_kinds: str = "digest_issue,paper_snapshot",
    roles: str = "owner,editor",
    max_papers_per_digest: int = 10,
) -> None:
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_RESULT_COLLECT_ENABLED",
        "true" if enabled else "false",
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_RESULT_COLLECT_ALLOWED_SHARE_KINDS",
        share_kinds,
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_RESULT_COLLECT_ALLOWED_ROLES",
        roles,
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_RESULT_COLLECT_MAX_PAPERS_PER_DIGEST",
        str(max_papers_per_digest),
    )
    get_settings.cache_clear()


def create_user(client, headers, *, email: str, name: str = "Collect User") -> dict:
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


def create_self_service_grant(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/subscription-self-service-grants",
        headers=headers,
        json={"user_id": user_id, "channel": ChannelType.OFFICIAL_ACCOUNT.value},
    )
    assert response.status_code == 201
    return response.json()


def create_mini_grant(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/mini-read-grants",
        headers=headers,
        json={"user_id": user_id, "grant_type": MiniReadGrantType.PREVIEW.value},
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


def create_digest_issue_with_payload(
    session, *, user_id: str, title: str, papers: list[dict]
) -> dict:
    issue = PulseDigestIssue(
        user_id=UUID(user_id),
        issue_date=utcnow().date(),
        status=PulseDigestIssueStatus.PUBLISHED,
        title=title,
        summary=f"{title} summary",
        highlight_count=min(2, len(papers)),
        selected_card_count=len(papers) + 1,
        content_payload={
            "sections": [
                {
                    "kind": "today_focus",
                    "title": "Today Focus",
                    "item_count": 2,
                    "items": [
                        {
                            "sort_order": 0,
                            "pulse_card_id": "00000000-0000-0000-0000-000000000001",
                            "card_type": "today_suggestion",
                            "source_paper_id": papers[0]["id"],
                            "title": papers[0]["title"],
                            "summary": "Focus this paper today",
                            "paper": {
                                "id": papers[0]["id"],
                                "user_id": user_id,
                                "title": papers[0]["title"],
                                "type": papers[0]["type"],
                                "stage": papers[0]["stage"],
                                "venue": papers[0]["venue"],
                                "priority": papers[0]["priority"],
                                "next_action": papers[0]["next_action"],
                                "blocker": papers[0]["blocker"],
                                "last_touch_at": papers[0]["last_touch_at"],
                                "progress_percentage": 100,
                            },
                        },
                        {
                            "sort_order": 1,
                            "pulse_card_id": "00000000-0000-0000-0000-000000000002",
                            "card_type": "signal_change",
                            "source_paper_id": papers[1]["id"],
                            "title": papers[1]["title"],
                            "summary": "Signal change detected",
                            "paper": {
                                "id": papers[1]["id"],
                                "user_id": user_id,
                                "title": papers[1]["title"],
                                "type": papers[1]["type"],
                                "stage": papers[1]["stage"],
                                "venue": papers[1]["venue"],
                                "priority": papers[1]["priority"],
                                "next_action": papers[1]["next_action"],
                                "blocker": papers[1]["blocker"],
                                "last_touch_at": papers[1]["last_touch_at"],
                                "progress_percentage": 100,
                            },
                        },
                    ],
                },
                {
                    "kind": "signal_updates",
                    "title": "Signal Updates",
                    "item_count": 1,
                    "items": [
                        {
                            "sort_order": 2,
                            "pulse_card_id": "00000000-0000-0000-0000-000000000003",
                            "card_type": "signal_change",
                            "source_paper_id": papers[0]["id"],
                            "title": papers[0]["title"],
                            "summary": "Duplicate reference to first paper",
                            "paper": {
                                "id": papers[0]["id"],
                                "user_id": user_id,
                                "title": papers[0]["title"],
                                "type": papers[0]["type"],
                                "stage": papers[0]["stage"],
                                "venue": papers[0]["venue"],
                                "priority": papers[0]["priority"],
                                "next_action": papers[0]["next_action"],
                                "blocker": papers[0]["blocker"],
                                "last_touch_at": papers[0]["last_touch_at"],
                                "progress_percentage": 100,
                            },
                        }
                    ],
                },
            ],
            "highlights": [],
            "items": [],
        },
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return {"id": str(issue.id), "title": issue.title}


def test_collect_preview_returns_paper_snapshot_and_public_bootstrap_collection_reserve(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_result_collect(monkeypatch)
    user = create_user(client, operator_headers, email="collect-preview@example.com")
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Collectable Paper")
    share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.PAPER_SNAPSHOT,
        paper_id=paper["id"],
    )
    self_service = create_self_service_grant(client, operator_headers, user_id=user["id"])
    headers = {"Authorization": f"Bearer {self_service['plain_text_token']}"}

    bootstrap = client.get(f"/result-shares/{share['plain_text_token']}/bootstrap")
    preview = client.get(
        f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect-preview",
        headers=headers,
    )

    assert bootstrap.status_code == 200
    assert bootstrap.json()["collection_reserve"]["supported"] is True
    assert bootstrap.json()["collection_reserve"]["source_files_included"] is False
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["can_collect"] is False
    assert payload["reason_codes"] == ["no_eligible_workspace_membership"]
    assert len(payload["collectable_items"]) == 1
    assert payload["collectable_items"][0]["paper_id"] == paper["id"]


def test_digest_collect_preview_dedupes_papers_and_workspace_board_is_not_collectable(
    client,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    enable_result_collect(monkeypatch)
    user = create_user(client, operator_headers, email="collect-digest@example.com")
    paper_a = create_paper(client, operator_headers, user_id=user["id"], title="Digest Paper A")
    paper_b = create_paper(client, operator_headers, user_id=user["id"], title="Digest Paper B")
    digest_issue = create_digest_issue_with_payload(
        session,
        user_id=user["id"],
        title="Digest Collect Issue",
        papers=[paper_a, paper_b],
    )
    digest_share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.DIGEST_ISSUE,
        digest_issue_id=digest_issue["id"],
    )
    workspace = create_workspace(
        client, operator_headers, slug="board-collect", name="Board Collect"
    )
    workspace_share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.WORKSPACE_BOARD,
        workspace_id=workspace["id"],
    )
    add_workspace_member(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        user_id=user["id"],
        role=GroupWorkspaceMemberRole.EDITOR.value,
    )
    self_service = create_self_service_grant(client, operator_headers, user_id=user["id"])
    headers = {"Authorization": f"Bearer {self_service['plain_text_token']}"}

    digest_preview = client.get(
        f"/subscription-self-service/result-shares/{digest_share['plain_text_token']}/collect-preview",
        headers=headers,
    )
    board_preview = client.get(
        f"/subscription-self-service/result-shares/{workspace_share['plain_text_token']}/collect-preview",
        headers=headers,
    )

    assert digest_preview.status_code == 200
    digest_payload = digest_preview.json()
    assert digest_payload["can_collect"] is True
    assert [item["paper_id"] for item in digest_payload["collectable_items"]] == [
        paper_a["id"],
        paper_b["id"],
    ]
    assert len(digest_payload["eligible_workspaces"]) == 1

    assert board_preview.status_code == 200
    assert board_preview.json()["can_collect"] is False
    assert board_preview.json()["reason_codes"] == ["share_kind_not_collectable"]


def test_self_service_collect_succeeds_and_repeat_returns_already_present(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_result_collect(monkeypatch)
    user = create_user(client, operator_headers, email="collect-ok@example.com")
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Workspace Collect")
    workspace = create_workspace(client, operator_headers, slug="collect-ok", name="Collect OK")
    add_workspace_member(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        user_id=user["id"],
        role=GroupWorkspaceMemberRole.EDITOR.value,
    )
    share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.PAPER_SNAPSHOT,
        paper_id=paper["id"],
    )
    self_service = create_self_service_grant(client, operator_headers, user_id=user["id"])
    headers = {"Authorization": f"Bearer {self_service['plain_text_token']}"}

    first = client.post(
        f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
        headers=headers,
        json={"workspace_id": workspace["id"]},
    )
    repeated = client.post(
        f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
        headers=headers,
        json={"workspace_id": workspace["id"]},
    )
    collections = client.get(
        "/subscription-self-service/workspace-result-collections",
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["action"] == "collected"
    assert first.json()["collected_results"][0]["status"] == "collected"
    assert repeated.status_code == 200
    assert repeated.json()["action"] == "already_present"
    assert repeated.json()["collected_results"][0]["status"] == "already_present"
    assert collections.status_code == 200
    assert collections.json()[0]["workspace"]["id"] == workspace["id"]
    assert collections.json()[0]["paper"]["paper_id"] == paper["id"]


def test_collect_rejects_viewer_archived_workspace_and_invalid_paper_selection(
    client,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    enable_result_collect(monkeypatch)
    user = create_user(client, operator_headers, email="collect-reject@example.com")
    paper_a = create_paper(client, operator_headers, user_id=user["id"], title="Reject Paper A")
    paper_b = create_paper(client, operator_headers, user_id=user["id"], title="Reject Paper B")
    digest_issue = create_digest_issue_with_payload(
        session,
        user_id=user["id"],
        title="Reject Digest",
        papers=[paper_a, paper_b],
    )
    digest_share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.DIGEST_ISSUE,
        digest_issue_id=digest_issue["id"],
    )
    viewer_workspace = create_workspace(
        client,
        operator_headers,
        slug="collect-viewer",
        name="Collect Viewer",
    )
    archived_workspace = create_workspace(
        client,
        operator_headers,
        slug="collect-archived",
        name="Collect Archived",
    )
    add_workspace_member(
        client,
        operator_headers,
        workspace_id=viewer_workspace["id"],
        user_id=user["id"],
        role=GroupWorkspaceMemberRole.VIEWER.value,
    )
    add_workspace_member(
        client,
        operator_headers,
        workspace_id=archived_workspace["id"],
        user_id=user["id"],
        role=GroupWorkspaceMemberRole.EDITOR.value,
    )
    archived = client.patch(
        f"/admin/group-workspaces/{archived_workspace['id']}",
        headers=operator_headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    self_service = create_self_service_grant(client, operator_headers, user_id=user["id"])
    headers = {"Authorization": f"Bearer {self_service['plain_text_token']}"}

    missing_selection = client.post(
        f"/subscription-self-service/result-shares/{digest_share['plain_text_token']}/collect",
        headers=headers,
        json={"workspace_id": archived_workspace["id"]},
    )
    viewer_collect = client.post(
        f"/subscription-self-service/result-shares/{digest_share['plain_text_token']}/collect",
        headers=headers,
        json={"workspace_id": viewer_workspace["id"], "paper_ids": [paper_a["id"]]},
    )
    invalid_paper = client.post(
        f"/subscription-self-service/result-shares/{digest_share['plain_text_token']}/collect",
        headers=headers,
        json={
            "workspace_id": archived_workspace["id"],
            "paper_ids": ["00000000-0000-0000-0000-000000000099"],
        },
    )

    assert missing_selection.status_code == 200
    assert "workspace_archived" in missing_selection.json()["notes"]
    assert viewer_collect.status_code == 200
    assert viewer_collect.json()["action"] == "rejected"
    assert "role_not_allowed" in viewer_collect.json()["notes"]
    assert invalid_paper.status_code == 200
    assert "workspace_archived" in invalid_paper.json()["notes"]


def test_digest_collect_requires_explicit_selection_and_mini_cannot_collect(
    client,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    enable_result_collect(monkeypatch)
    user = create_user(client, operator_headers, email="collect-mini@example.com")
    paper_a = create_paper(client, operator_headers, user_id=user["id"], title="Mini Paper A")
    paper_b = create_paper(client, operator_headers, user_id=user["id"], title="Mini Paper B")
    digest_issue = create_digest_issue_with_payload(
        session,
        user_id=user["id"],
        title="Mini Digest",
        papers=[paper_a, paper_b],
    )
    share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.DIGEST_ISSUE,
        digest_issue_id=digest_issue["id"],
    )
    workspace = create_workspace(client, operator_headers, slug="collect-mini", name="Collect Mini")
    add_workspace_member(
        client,
        operator_headers,
        workspace_id=workspace["id"],
        user_id=user["id"],
        role=GroupWorkspaceMemberRole.OWNER.value,
    )
    self_service = create_self_service_grant(client, operator_headers, user_id=user["id"])
    mini = create_mini_grant(client, operator_headers, user_id=user["id"])
    self_headers = {"Authorization": f"Bearer {self_service['plain_text_token']}"}
    mini_headers = {"Authorization": f"Bearer {mini['plain_text_token']}"}

    missing_selection = client.post(
        f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
        headers=self_headers,
        json={"workspace_id": workspace["id"]},
    )
    selected = client.post(
        f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
        headers=self_headers,
        json={"workspace_id": workspace["id"], "paper_ids": [paper_a["id"]]},
    )
    mini_collect = client.post(
        f"/subscription-self-service/result-shares/{share['plain_text_token']}/collect",
        headers=mini_headers,
        json={"workspace_id": workspace["id"], "paper_ids": [paper_a["id"]]},
    )
    mini_reserve = client.get("/mini/subscription-reserve", headers=mini_headers)
    admin_records = client.get(
        "/admin/group-workspace-result-collect-records",
        headers=operator_headers,
        params={"workspace_id": workspace["id"]},
    )

    assert missing_selection.status_code == 200
    assert missing_selection.json()["notes"] == ["paper_selection_required"]
    assert selected.status_code == 200
    assert selected.json()["action"] == "collected"
    assert mini_collect.status_code == 401
    assert mini_reserve.status_code == 200
    assert mini_reserve.json()["workspace_collect_reserve"]["supported"] is True
    assert mini_reserve.json()["workspace_collect_reserve"]["supported_share_kinds"] == [
        "digest_issue",
        "paper_snapshot",
    ]
    assert admin_records.status_code == 200
    assert admin_records.json()[0]["record"]["status"] == "collected"
    assert "source files" not in json.dumps(admin_records.json())
