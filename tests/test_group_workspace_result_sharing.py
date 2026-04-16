from __future__ import annotations

import json
from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    GroupWorkspaceMemberRole,
    PaperType,
    ResultShareKind,
    SignalSource,
)


def create_user(client, headers, *, email: str, name: str = "Workspace User") -> dict:
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


def create_paper(
    client,
    headers,
    *,
    user_id: str,
    title: str,
    source_links: list[str] | None = None,
) -> dict:
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
            "source_links": source_links
            or [f"https://example.local/{title.lower().replace(' ', '-')}"],
            "last_touch_at": (utcnow() - timedelta(days=3)).isoformat(),
            "next_action": "Review the latest signal delta",
            "blocker": None,
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


def create_workspace(client, headers, *, slug: str, name: str) -> dict:
    response = client.post(
        "/admin/group-workspaces",
        headers=headers,
        json={"slug": slug, "name": name, "description": f"{name} description"},
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
    expires_at: str | None = None,
) -> dict:
    payload: dict[str, object] = {"share_kind": share_kind.value}
    if workspace_id is not None:
        payload["workspace_id"] = workspace_id
    if digest_issue_id is not None:
        payload["digest_issue_id"] = digest_issue_id
    if paper_id is not None:
        payload["paper_id"] = paper_id
    if expires_at is not None:
        payload["expires_at"] = expires_at
    response = client.post("/admin/result-share-grants", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def create_digest_issue(client, headers, *, user_id: str, title: str) -> dict:
    paper = create_paper(client, headers, user_id=user_id, title=title)
    add_signal_pair(client, headers, paper_id=paper["id"])
    pulse_run = client.post(f"/pulse/run/{user_id}", headers=headers)
    assert pulse_run.status_code == 200
    issues = client.get("/admin/digest-issues", headers=headers, params={"user_id": user_id})
    assert issues.status_code == 200
    return issues.json()[0]


def test_create_list_update_workspace_and_manage_members_and_papers(
    client,
    operator_headers,
) -> None:
    owner = create_user(client, operator_headers, email="workspace-owner@example.com", name="Owner")
    viewer = create_user(
        client,
        operator_headers,
        email="workspace-viewer@example.com",
        name="Viewer",
    )
    paper = create_paper(client, operator_headers, user_id=owner["id"], title="Workspace Paper")

    workspace = create_workspace(
        client,
        operator_headers,
        slug="materials-group",
        name="Materials Group",
    )
    listed = client.get("/admin/group-workspaces", headers=operator_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["slug"] == "materials-group"

    updated = client.patch(
        f"/admin/group-workspaces/{workspace['id']}",
        headers=operator_headers,
        json={"name": "Materials Group Updated", "status": "archived"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Materials Group Updated"
    assert updated.json()["status"] == "archived"

    added_member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": owner["id"], "role": GroupWorkspaceMemberRole.OWNER.value},
    )
    assert added_member.status_code == 201
    duplicate_member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": owner["id"], "role": GroupWorkspaceMemberRole.OWNER.value},
    )
    assert duplicate_member.status_code == 409
    second_member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": viewer["id"], "role": GroupWorkspaceMemberRole.VIEWER.value},
    )
    assert second_member.status_code == 201

    added_paper = client.post(
        f"/admin/group-workspaces/{workspace['id']}/papers",
        headers=operator_headers,
        json={"paper_id": paper["id"]},
    )
    assert added_paper.status_code == 201
    duplicate_paper = client.post(
        f"/admin/group-workspaces/{workspace['id']}/papers",
        headers=operator_headers,
        json={"paper_id": paper["id"]},
    )
    assert duplicate_paper.status_code == 409

    removed_member = client.delete(
        f"/admin/group-workspaces/{workspace['id']}/members/{second_member.json()['id']}",
        headers=operator_headers,
    )
    assert removed_member.status_code == 204
    removed_paper = client.delete(
        f"/admin/group-workspaces/{workspace['id']}/papers/{paper['id']}",
        headers=operator_headers,
    )
    assert removed_paper.status_code == 204


def test_workspace_board_renders_deterministic_safe_snapshots(
    client,
    operator_headers,
) -> None:
    owner = create_user(
        client,
        operator_headers,
        email="board-owner@example.com",
        name="Board Owner",
    )
    paper = create_paper(
        client,
        operator_headers,
        user_id=owner["id"],
        title="Board Paper",
        source_links=["/Users/zhangbin/GitHub/research-pulse-cn/local-board.pdf"],
    )
    add_signal_pair(client, operator_headers, paper_id=paper["id"])
    workspace = create_workspace(client, operator_headers, slug="board-space", name="Board Space")
    member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": owner["id"], "role": GroupWorkspaceMemberRole.OWNER.value},
    )
    assert member.status_code == 201
    added_paper = client.post(
        f"/admin/group-workspaces/{workspace['id']}/papers",
        headers=operator_headers,
        json={"paper_id": paper["id"]},
    )
    assert added_paper.status_code == 201

    board = client.get(f"/admin/group-workspaces/{workspace['id']}/board", headers=operator_headers)
    assert board.status_code == 200
    payload = board.json()
    assert payload["member_count"] == 1
    assert payload["paper_count"] == 1
    assert payload["members"][0]["email"] == owner["email"]
    assert (
        payload["papers"][0]["latest_signal_summary"]["source"] == SignalSource.GOOGLE_SCHOLAR.value
    )
    serialized = json.dumps(payload)
    assert "/Users/zhangbin/GitHub/research-pulse-cn/local-board.pdf" not in serialized
    assert "openid" not in serialized
    assert "unionid" not in serialized


def test_result_share_grants_resolve_digest_paper_and_workspace_safely(
    client,
    operator_headers,
) -> None:
    owner = create_user(
        client,
        operator_headers,
        email="share-owner@example.com",
        name="Share Owner",
    )
    paper = create_paper(
        client,
        operator_headers,
        user_id=owner["id"],
        title="Share Paper",
        source_links=["/Users/zhangbin/GitHub/research-pulse-cn/share-source.pdf"],
    )
    add_signal_pair(client, operator_headers, paper_id=paper["id"])
    workspace = create_workspace(client, operator_headers, slug="share-space", name="Share Space")
    member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": owner["id"], "role": GroupWorkspaceMemberRole.OWNER.value},
    )
    assert member.status_code == 201
    workspace_paper = client.post(
        f"/admin/group-workspaces/{workspace['id']}/papers",
        headers=operator_headers,
        json={"paper_id": paper["id"]},
    )
    assert workspace_paper.status_code == 201
    digest_issue = create_digest_issue(
        client,
        operator_headers,
        user_id=owner["id"],
        title="Shared Digest Paper",
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
    workspace_share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.WORKSPACE_BOARD,
        workspace_id=workspace["id"],
    )

    listed = client.get("/admin/result-share-grants", headers=operator_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    paper_bootstrap = client.get(f"/result-shares/{paper_share['plain_text_token']}/bootstrap")
    paper_content = client.get(f"/result-shares/{paper_share['plain_text_token']}/content")
    digest_content = client.get(f"/result-shares/{digest_share['plain_text_token']}/content")
    workspace_content = client.get(f"/result-shares/{workspace_share['plain_text_token']}/content")

    assert paper_bootstrap.status_code == 200
    assert paper_bootstrap.json()["grant"]["share_kind"] == ResultShareKind.PAPER_SNAPSHOT.value
    assert paper_content.status_code == 200
    assert paper_content.json()["share_kind"] == ResultShareKind.PAPER_SNAPSHOT.value
    assert paper_content.json()["owner_email"] is None

    assert digest_content.status_code == 200
    digest_payload = digest_content.json()
    assert digest_payload["share_kind"] == ResultShareKind.DIGEST_ISSUE.value
    assert digest_payload["fallback_mode"] in {"structured", "highlights_only"}

    assert workspace_content.status_code == 200
    workspace_payload = workspace_content.json()
    assert workspace_payload["share_kind"] == ResultShareKind.WORKSPACE_BOARD.value
    assert workspace_payload["members"][0]["email"] is None
    assert workspace_payload["papers"][0]["owner_email"] is None

    for payload in (
        paper_content.json(),
        digest_payload,
        workspace_payload,
    ):
        serialized = json.dumps(payload)
        assert "/Users/zhangbin/GitHub/research-pulse-cn/share-source.pdf" not in serialized
        assert "openid" not in serialized
        assert "unionid" not in serialized


def test_revoked_and_expired_result_share_grants_are_rejected(
    client,
    operator_headers,
) -> None:
    owner = create_user(
        client,
        operator_headers,
        email="share-expiry@example.com",
        name="Expiry Owner",
    )
    workspace = create_workspace(client, operator_headers, slug="expiry-space", name="Expiry Space")
    member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": owner["id"], "role": GroupWorkspaceMemberRole.OWNER.value},
    )
    assert member.status_code == 201

    active_share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.WORKSPACE_BOARD,
        workspace_id=workspace["id"],
    )
    revoked = client.post(
        f"/admin/result-share-grants/{active_share['grant']['id']}/revoke",
        headers=operator_headers,
    )
    assert revoked.status_code == 200
    revoked_bootstrap = client.get(f"/result-shares/{active_share['plain_text_token']}/bootstrap")
    assert revoked_bootstrap.status_code == 401

    expired_share = create_result_share_grant(
        client,
        operator_headers,
        share_kind=ResultShareKind.WORKSPACE_BOARD,
        workspace_id=workspace["id"],
        expires_at=(utcnow() - timedelta(minutes=5)).isoformat(),
    )
    expired_content = client.get(f"/result-shares/{expired_share['plain_text_token']}/content")
    assert expired_content.status_code == 401
