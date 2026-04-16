from __future__ import annotations

import json
from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import GroupWorkspaceMemberRole, PaperType, SignalSource


def create_user(client, headers, *, email: str, name: str = "Workbench User") -> dict:
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
            or [f"https://example.local/papers/{title.lower().replace(' ', '-')}"],
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


def create_watch_profile(
    client,
    headers,
    *,
    user_id: str,
    paper_id: str | None,
    label: str,
    enabled: bool = True,
) -> dict:
    response = client.post(
        "/research-watch-profiles",
        headers=headers,
        json={
            "user_id": user_id,
            "paper_id": paper_id,
            "label": label,
            "enabled": enabled,
            "topics": ["materials", "citations"],
            "keywords": ["diffusion", "grain boundary"],
            "venues": ["JOM"],
            "authors_of_interest": ["Dr. Smith"],
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


def create_digest_issue(client, headers, *, user_id: str, title: str) -> dict:
    paper = create_paper(client, headers, user_id=user_id, title=title)
    add_signal_pair(client, headers, paper_id=paper["id"])
    pulse_run = client.post(f"/pulse/run/{user_id}", headers=headers)
    assert pulse_run.status_code == 200
    issues = client.get("/admin/digest-issues", headers=headers, params={"user_id": user_id})
    assert issues.status_code == 200
    return issues.json()[0]


def test_user_workbench_users_support_search_limit_and_viewer_read(
    client, operator_headers, viewer_headers
):
    first = create_user(client, operator_headers, email="first@example.com", name="First User")
    second = create_user(client, operator_headers, email="second@example.com", name="Second User")
    create_paper(client, operator_headers, user_id=first["id"], title="First Paper")
    create_watch_profile(
        client,
        operator_headers,
        user_id=first["id"],
        paper_id=None,
        label="First Materials Watch",
    )
    workspace = create_workspace(client, operator_headers, slug="wb-space", name="Workbench Space")
    member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": first["id"], "role": GroupWorkspaceMemberRole.OWNER.value},
    )
    assert member.status_code == 201
    create_digest_issue(
        client, operator_headers, user_id=first["id"], title="Workbench Digest Paper"
    )

    response = client.get(
        "/admin/user-workbench/users",
        headers=viewer_headers,
        params={"q": "first", "limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == first["id"]
    assert payload[0]["paper_count"] == 2
    assert payload[0]["watch_profile_count"] == 1
    assert payload[0]["workspace_count"] == 1
    assert payload[0]["latest_digest_issue_summary"]["title"]
    assert second["id"] not in {item["id"] for item in payload}


def test_user_workbench_user_detail_includes_safe_drilldown_context(client, operator_headers):
    user = create_user(client, operator_headers, email="detail@example.com", name="Detail User")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Detail Paper",
        source_links=["/Users/zhangbin/GitHub/research-pulse-cn/private.pdf"],
    )
    create_watch_profile(
        client,
        operator_headers,
        user_id=user["id"],
        paper_id=paper["id"],
        label="Detail Watch",
    )
    workspace = create_workspace(client, operator_headers, slug="detail-space", name="Detail Space")
    member = client.post(
        f"/admin/group-workspaces/{workspace['id']}/members",
        headers=operator_headers,
        json={"user_id": user["id"], "role": GroupWorkspaceMemberRole.EDITOR.value},
    )
    assert member.status_code == 201
    create_digest_issue(client, operator_headers, user_id=user["id"], title="Detail Digest Paper")

    response = client.get(f"/admin/user-workbench/users/{user['id']}", headers=operator_headers)

    assert response.status_code == 200
    payload = response.json()
    payload_text = json.dumps(payload)
    assert payload["user"]["id"] == user["id"]
    assert len(payload["papers"]) == 2
    assert payload["watch_profiles"][0]["label"] == "Detail Watch"
    assert payload["workspace_memberships"][0]["slug"] == "detail-space"
    assert payload["user"]["latest_digest_issue_summary"]["title"]
    assert "/Users/zhangbin/GitHub" not in payload_text
    assert "source_links" not in payload_text


def test_user_workbench_paper_detail_and_watch_profile_filters_are_safe(client, operator_headers):
    user = create_user(client, operator_headers, email="paper@example.com", name="Paper User")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Paper Drilldown",
        source_links=["/Users/zhangbin/GitHub/research-pulse-cn/local-path.pdf"],
    )
    other_paper = create_paper(client, operator_headers, user_id=user["id"], title="Other Paper")
    add_signal_pair(client, operator_headers, paper_id=paper["id"])
    create_watch_profile(
        client,
        operator_headers,
        user_id=user["id"],
        paper_id=paper["id"],
        label="Enabled Watch",
        enabled=True,
    )
    create_watch_profile(
        client,
        operator_headers,
        user_id=user["id"],
        paper_id=other_paper["id"],
        label="Disabled Watch",
        enabled=False,
    )

    paper_detail = client.get(
        f"/admin/user-workbench/papers/{paper['id']}", headers=operator_headers
    )
    watch_profiles = client.get(
        "/admin/user-workbench/watch-profiles",
        headers=operator_headers,
        params={
            "user_id": user["id"],
            "paper_id": paper["id"],
            "enabled": "true",
            "q": "enabled",
        },
    )

    assert paper_detail.status_code == 200
    assert watch_profiles.status_code == 200

    paper_payload = paper_detail.json()
    watch_payload = watch_profiles.json()
    paper_text = json.dumps(paper_payload)

    assert paper_payload["paper"]["title"] == "Paper Drilldown"
    assert paper_payload["paper"]["latest_signal_summary"]["citation_count"] == 14
    assert paper_payload["linked_watch_profiles"][0]["label"] == "Enabled Watch"
    assert "/Users/zhangbin/GitHub" not in paper_text
    assert "source_links" not in paper_text
    assert len(watch_payload) == 1
    assert watch_payload[0]["paper_id"] == paper["id"]
    assert watch_payload[0]["label"] == "Enabled Watch"
