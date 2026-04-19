from datetime import UTC, datetime

from research_pulse_cn.db.models import DeliveryJob
from research_pulse_cn.domain.enums import PaperImportSourceFormat, PaperType


def create_user(client, headers, *, email: str = "desktop-notification@example.com") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Desktop Notification User",
            "email": email,
            "field": "Materials",
            "interests": ["diffusion"],
            "watched_topics": ["alloys"],
            "watched_venues": ["Acta Materialia"],
            "reminder_preferences": {"timezone": "Asia/Shanghai"},
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
    stage: str = "inbox",
    priority: int = 3,
    venue: str | None = "Acta Materialia",
    identifiers: dict | None = None,
    next_action: str | None = None,
    last_touch_at: str | None = None,
) -> dict:
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": PaperType.PUBLISHED.value,
            "stage": stage,
            "venue": venue,
            "identifiers": identifiers or {},
            "source_links": [f"https://example.local/papers/{title.lower().replace(' ', '-')}"],
            "next_action": next_action,
            "priority": priority,
            "last_touch_at": last_touch_at,
        },
    )
    assert response.status_code == 201
    return response.json()


def update_progress(client, headers, *, paper_id: str, **payload) -> dict:
    response = client.patch(f"/papers/{paper_id}/progress", headers=headers, json=payload)
    assert response.status_code == 200
    return response.json()


def generate_desktop_notification(client, headers, *, user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "timezone": "Asia/Shanghai",
        "max_items": 3,
        "include_low_priority": False,
        "include_archived": False,
        "source_format_filter": [],
        "title_prefix": "今日科研 Pulse",
        "include_actions": True,
        "dry_run": True,
    }
    payload.update(overrides)
    response = client.post(
        "/pulse/papers/desktop-notification/draft",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_empty_library_generates_desktop_notification_draft_without_delivery_jobs(
    client,
    viewer_headers,
    operator_headers,
    session,
) -> None:
    user = create_user(client, operator_headers, email="desktop-empty@example.com")

    assert session.query(DeliveryJob).count() == 0
    payload = generate_desktop_notification(client, viewer_headers, user_id=user["id"])

    assert payload["notification_type"] == "daily_research_pulse"
    assert payload["delivery_state"] == "draft"
    assert payload["urgency"] == "low"
    assert payload["badge_count"] == 0
    assert payload["items"] == []
    assert payload["actions"] == []
    assert payload["deep_link"].startswith("research-pulse://pulse/daily/")
    assert "已发送成功" not in payload["body"]
    assert "已推送成功" not in payload["body"]

    session.expire_all()
    assert session.query(DeliveryJob).count() == 0


def test_desktop_notification_builds_title_body_actions_and_payload_preview(
    client,
    viewer_headers,
    operator_headers,
    session,
) -> None:
    user = create_user(client, operator_headers, email="desktop-rich@example.com")

    urgent = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Urgent Focus Paper",
        stage="reviewing",
        priority=5,
        identifiers={
            "doi": "10.1000/focus",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang"],
            "import_year": 2025,
            "progress_workbench": {"reading_status": "reading", "tags": ["重点"]},
        },
        next_action="先整理方法对比表",
        last_touch_at=datetime(2026, 4, 19, 9, 0, tzinfo=UTC).isoformat(),
    )
    update_progress(
        client,
        operator_headers,
        paper_id=urgent["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="urgent",
        next_action="先整理方法对比表",
    )

    metadata_gap = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Metadata Gap PDF",
        stage="inbox",
        priority=4,
        venue=None,
        identifiers={
            "import_source_format": PaperImportSourceFormat.PDF_FOLDER.value,
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=metadata_gap["id"],
        research_stage="inbox",
        reading_status="unread",
        priority="high",
    )

    triage = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="New Triage Paper",
        stage="triage",
        priority=3,
        identifiers={
            "import_source_format": PaperImportSourceFormat.TABULAR.value,
            "import_authors": ["Bo Li"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=triage["id"],
        research_stage="triage",
        reading_status="unread",
    )

    payload = generate_desktop_notification(client, viewer_headers, user_id=user["id"])

    assert payload["title"] == "今日科研 Pulse：1 个重点事项"
    assert "有 1 篇高优先级论文" in payload["body"]
    assert payload["urgency"] == "high"
    assert payload["badge_count"] >= 2
    assert payload["delivery_state"] == "draft"
    assert payload["payload_preview"]["notification_title"] == payload["title"]
    assert payload["payload_preview"]["notification_body"] == payload["body"]
    assert (
        payload["payload_preview"]["source_pulse_draft_id"]
        == payload["source_research_pulse_draft_id"]
    )
    assert payload["payload_preview"]["delivery_state"] == "draft"
    assert payload["deep_link"].startswith("research-pulse://pulse/daily/")
    assert {item["title"] for item in payload["items"]} >= {
        "Urgent Focus Paper",
        "Metadata Gap PDF",
    }
    labels = {action["label"] for action in payload["actions"]}
    assert labels >= {"查看今日 Pulse", "查看下一步动作", "补全元数据", "筛选新导入论文"}
    assert all(action["deep_link"].startswith("research-pulse://") for action in payload["actions"])
    assert "已发送成功" not in payload["body"]
    assert "已推送成功" not in payload["body"]

    session.expire_all()
    assert session.query(DeliveryJob).count() == 0


def test_include_actions_false_returns_empty_actions_with_warning(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="desktop-actions-off@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Action Paper",
        stage="reviewing",
        priority=5,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang"],
            "progress_workbench": {"reading_status": "reading"},
        },
        next_action="继续整理实验对比",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="urgent",
        next_action="继续整理实验对比",
    )

    payload = generate_desktop_notification(
        client,
        viewer_headers,
        user_id=user["id"],
        include_actions=False,
    )

    assert payload["actions"] == []
    assert any("关闭 actions" in warning for warning in payload["warnings"])


def test_source_format_filter_and_max_items_are_applied(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="desktop-filter@example.com")
    first = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="First CSL Paper",
        stage="reviewing",
        priority=5,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang"],
            "progress_workbench": {"reading_status": "reading"},
        },
        next_action="先看方法部分",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=first["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="urgent",
        next_action="先看方法部分",
    )
    second = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Second CSL Paper",
        stage="reviewing",
        priority=4,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Bo Li"],
            "progress_workbench": {"reading_status": "skimming"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=second["id"],
        research_stage="reviewing",
        reading_status="skimming",
        priority="high",
    )
    third = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="PDF Placeholder",
        stage="inbox",
        priority=4,
        venue=None,
        identifiers={
            "import_source_format": PaperImportSourceFormat.PDF_FOLDER.value,
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=third["id"],
        research_stage="inbox",
        reading_status="unread",
        priority="high",
    )

    filtered = generate_desktop_notification(
        client,
        viewer_headers,
        user_id=user["id"],
        source_format_filter=[PaperImportSourceFormat.CSL_JSON.value],
        max_items=1,
    )

    assert filtered["total_source_papers"] == 2
    assert filtered["total_items"] == 1
    assert len(filtered["items"]) == 1
    assert filtered["items"][0]["source_format"] == PaperImportSourceFormat.CSL_JSON.value


def test_include_archived_true_allows_archived_items_in_draft(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="desktop-archived@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Archived Focus Paper",
        stage="reviewing",
        priority=5,
        identifiers={
            "doi": "10.1000/archived",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Archived User"],
            "progress_workbench": {"reading_status": "archived"},
        },
        next_action="后续补写实验记录",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper["id"],
        research_stage="reviewing",
        reading_status="archived",
        priority="urgent",
        next_action="后续补写实验记录",
    )

    excluded = generate_desktop_notification(client, viewer_headers, user_id=user["id"])
    included = generate_desktop_notification(
        client,
        viewer_headers,
        user_id=user["id"],
        include_archived=True,
    )

    assert excluded["total_source_papers"] == 0
    assert included["total_source_papers"] == 1
    assert included["items"][0]["title"] == "Archived Focus Paper"


def test_include_low_priority_true_allows_low_priority_next_action_into_notification(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="desktop-low-priority@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Low Priority Action Paper",
        stage="relevant",
        priority=1,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Low Priority User"],
            "progress_workbench": {"reading_status": "unread"},
        },
        next_action="后续补读方法细节",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper["id"],
        research_stage="relevant",
        reading_status="unread",
        priority="low",
        next_action="后续补读方法细节",
    )

    excluded = generate_desktop_notification(client, viewer_headers, user_id=user["id"])
    included = generate_desktop_notification(
        client,
        viewer_headers,
        user_id=user["id"],
        include_low_priority=True,
    )

    assert excluded["items"] == []
    assert included["items"][0]["title"] == "Low Priority Action Paper"
