from datetime import UTC, datetime
from uuid import uuid4

from research_pulse_cn.domain.enums import (
    MiniProgramDetailType,
    PaperImportSourceFormat,
    PaperType,
)


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Mini Detail User",
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


def generate_mini_program_detail(client, headers, *, user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "detail_type": MiniProgramDetailType.DAILY_PULSE.value,
        "timezone": "Asia/Shanghai",
        "max_items": 5,
        "include_low_priority": False,
        "include_archived": False,
        "source_format_filter": [],
        "share_safe": True,
        "dry_run": True,
    }
    payload.update(overrides)
    response = client.post(
        "/pulse/papers/mini-program/detail/preview",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_empty_library_generates_daily_pulse_detail_preview(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-empty@example.com")

    payload = generate_mini_program_detail(client, viewer_headers, user_id=user["id"])

    assert payload["detail_type"] == "daily_pulse"
    assert payload["delivery_state"] == "preview"
    assert payload["share_card"]["share_safe"] is True
    assert payload["navigation"]["current_path"].startswith("/pages/pulse/detail")
    assert any(card["card_type"] == "overview" for card in payload["cards"])
    assert any(card["empty_reason"] for card in payload["cards"] if card["card_type"] != "overview")
    assert "已发送成功" not in payload["summary"]
    assert "已推送成功" not in payload["summary"]
    assert "已登录微信" not in payload["summary"]


def test_paper_detail_shows_fields_and_share_safe_redaction(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-paper@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Paper Detail Preview",
        stage="reviewing",
        priority=4,
        identifiers={
            "doi": "10.1000/paper-detail",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang", "Bo Li"],
            "import_year": 2025,
            "import_raw_source_payload": {
                "abstract": "This is a raw abstract that should only appear as safe_abstract.",
                "debug_internal_note": "should never leak",
            },
            "progress_workbench": {
                "reading_status": "reading",
                "user_note": "private note should not leak",
                "research_note": "another private note",
                "tags": ["重点", "实验"],
            },
        },
        next_action="整理方法对比",
        last_touch_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC).isoformat(),
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="high",
        next_action="整理方法对比",
    )

    payload = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="paper",
        paper_id=paper["id"],
    )

    assert payload["title"] == "Paper Detail Preview"
    assert payload["subtitle"] == "论文详情预览"
    item = payload["cards"][0]["items"][0]
    assert item["authors"] == ["Alice Zhang", "Bo Li"]
    assert item["year"] == 2025
    assert item["doi"] == "10.1000/paper-detail"
    assert item["safe_abstract"]
    assert item["detail_path"].startswith("/pages/papers/detail?id=")
    assert payload["share_card"]["share_safe"] is True

    raw_json = str(payload)
    assert "raw_source_payload" not in raw_json
    assert "debug_internal_note" not in raw_json
    assert "private note should not leak" not in raw_json
    assert "another private note" not in raw_json


def test_paper_detail_missing_paper_id_returns_structured_warning(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-missing-paper@example.com")

    payload = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="paper",
    )

    assert any("paper_id" in warning for warning in payload["warnings"])
    assert payload["cards"][0]["empty_reason"]
    assert payload["total_items"] == 0


def test_paper_detail_unknown_paper_returns_structured_warning(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-unknown-paper@example.com")

    payload = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="paper",
        paper_id=str(uuid4()),
    )

    assert any("未找到对应的论文" in warning for warning in payload["warnings"])
    assert payload["cards"][0]["empty_reason"]
    assert payload["total_items"] == 0


def test_next_actions_detail_only_contains_papers_with_next_action_and_max_items(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-next-actions@example.com")
    paper_a = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Action Paper A",
        stage="reviewing",
        priority=5,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Author A"],
            "import_year": 2025,
            "progress_workbench": {"reading_status": "reading"},
        },
        next_action="先补实验对比",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper_a["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="urgent",
        next_action="先补实验对比",
    )
    paper_b = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Action Paper B",
        stage="relevant",
        priority=4,
        identifiers={
            "import_source_format": PaperImportSourceFormat.RIS.value,
            "import_authors": ["Author B"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "unread"},
        },
        next_action="补读方法细节",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper_b["id"],
        research_stage="relevant",
        reading_status="unread",
        priority="high",
        next_action="补读方法细节",
    )
    paper_c = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="No Action Paper",
        stage="reviewing",
        priority=4,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Author C"],
            "import_year": 2023,
            "progress_workbench": {"reading_status": "reading"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=paper_c["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="high",
    )

    payload = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="next_actions",
        max_items=1,
    )

    items = payload["cards"][0]["items"]
    assert len(items) == 1
    assert items[0]["title"] in {"Action Paper A", "Action Paper B"}
    assert payload["navigation"]["current_path"] == "/pages/papers/list?filter=next_action"


def test_metadata_attention_detail_filters_warning_papers_and_hides_raw_payload(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-metadata@example.com")
    warning_paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Metadata Warning Paper",
        stage="inbox",
        priority=4,
        venue=None,
        identifiers={
            "import_source_format": PaperImportSourceFormat.PDF_FOLDER.value,
            "import_raw_source_payload": {"abstract": "Raw payload that should stay hidden"},
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=warning_paper["id"],
        research_stage="inbox",
        reading_status="unread",
        priority="high",
    )
    clean_paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Clean Paper",
        stage="reviewing",
        priority=4,
        identifiers={
            "doi": "10.1000/clean",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Clean Author"],
            "import_year": 2025,
            "progress_workbench": {"reading_status": "reading"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=clean_paper["id"],
        research_stage="reviewing",
        reading_status="reading",
        priority="high",
    )

    payload = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="metadata_attention",
        share_safe=False,
    )

    titles = {item["title"] for item in payload["cards"][0]["items"]}
    assert "Metadata Warning Paper" in titles
    assert "Clean Paper" not in titles
    assert "raw_source_payload" not in str(payload)
    assert "Raw payload that should stay hidden" not in str(payload)


def test_triage_detail_respects_source_format_filter(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-triage@example.com")
    tabular_paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Tabular Triage Paper",
        stage="triage",
        priority=3,
        identifiers={
            "import_source_format": PaperImportSourceFormat.TABULAR.value,
            "import_authors": ["Tabular Author"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=tabular_paper["id"],
        research_stage="triage",
        reading_status="unread",
    )
    pdf_paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="PDF Triage Paper",
        stage="inbox",
        priority=3,
        identifiers={
            "import_source_format": PaperImportSourceFormat.PDF_FOLDER.value,
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    update_progress(
        client,
        operator_headers,
        paper_id=pdf_paper["id"],
        research_stage="inbox",
        reading_status="unread",
    )

    payload = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="triage",
        source_format_filter=[PaperImportSourceFormat.TABULAR.value],
    )

    titles = {item["title"] for item in payload["cards"][0]["items"]}
    assert titles == {"Tabular Triage Paper"}
    assert payload["share_card"]["path"] == "/pages/papers/list?filter=triage"


def test_next_actions_detail_include_low_priority_controls_visibility(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="mini-detail-low-priority@example.com")
    low_priority = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Low Priority Next Action",
        stage="relevant",
        priority=1,
        identifiers={
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Low Priority User"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "unread"},
        },
        next_action="后续补读方法细节",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=low_priority["id"],
        research_stage="relevant",
        reading_status="unread",
        priority="low",
        next_action="后续补读方法细节",
    )

    excluded = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="next_actions",
    )
    included = generate_mini_program_detail(
        client,
        viewer_headers,
        user_id=user["id"],
        detail_type="next_actions",
        include_low_priority=True,
    )

    assert excluded["cards"][0]["items"] == []
    assert {item["title"] for item in included["cards"][0]["items"]} == {"Low Priority Next Action"}
