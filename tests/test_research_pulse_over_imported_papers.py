from datetime import UTC, datetime

from research_pulse_cn.domain.enums import PaperImportSourceFormat, PaperType


def create_user(client, headers, *, email: str = "research-pulse@example.com") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Research Pulse User",
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


def generate_pulse(client, headers, *, user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "timezone": "Asia/Shanghai",
        "max_items_per_section": 3,
        "include_low_priority": False,
        "include_archived": False,
        "source_format_filter": [],
        "dry_run": True,
    }
    payload.update(overrides)
    response = client.post("/pulse/papers/daily", headers=headers, json=payload)
    assert response.status_code == 200
    return response.json()


def section(payload: dict, section_id: str) -> dict:
    return next(item for item in payload["sections"] if item["section_id"] == section_id)


def test_empty_library_generates_empty_research_pulse_with_warnings(
    client, viewer_headers, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="research-pulse-empty@example.com")

    payload = generate_pulse(client, viewer_headers, user_id=user["id"])

    assert payload["total_source_papers"] == 0
    assert payload["total_items"] == 0
    assert payload["warnings"]
    assert section(payload, "today_focus")["empty_reason"]
    assert section(payload, "newly_imported_triage")["empty_reason"]


def test_research_pulse_builds_sections_for_focus_reading_actions_metadata_and_triage(
    client, viewer_headers, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="research-pulse-sections@example.com")

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

    reading = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Reading Analysis Paper",
        stage="relevant",
        priority=3,
        identifiers={
            "doi": "10.1000/reading",
            "import_source_format": PaperImportSourceFormat.BIBTEX.value,
            "import_authors": ["Bo Li"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "skimming"},
        },
        last_touch_at=datetime(2026, 4, 19, 8, 0, tzinfo=UTC).isoformat(),
    )
    update_progress(
        client,
        operator_headers,
        paper_id=reading["id"],
        research_stage="relevant",
        reading_status="skimming",
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
            "import_authors": ["Chen Yu"],
            "import_year": 2023,
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

    payload = generate_pulse(client, viewer_headers, user_id=user["id"])

    focus = section(payload, "today_focus")
    continue_reading = section(payload, "continue_reading")
    next_actions = section(payload, "next_actions")
    metadata = section(payload, "metadata_attention")
    triage_section = section(payload, "newly_imported_triage")

    assert payload["title"].endswith("科研 Pulse 草稿")
    assert "今日已从" in payload["summary"]
    assert focus["items"][0]["title"] == "Urgent Focus Paper"
    assert continue_reading["items"][0]["title"] in {"Urgent Focus Paper", "Reading Analysis Paper"}
    assert next_actions["items"][0]["title"] == "Urgent Focus Paper"
    assert {item["title"] for item in metadata["items"]} >= {"Metadata Gap PDF"}
    assert {item["title"] for item in triage_section["items"]} >= {
        "Metadata Gap PDF",
        "New Triage Paper",
    }
    assert focus["items"][0]["reason"]
    assert focus["items"][0]["suggested_action"] == "先整理方法对比表"
    assert "该论文" in focus["items"][0]["reason"]
    assert "摘要" not in focus["items"][0]["reason"]


def test_section_sorting_is_stable_and_max_items_limit_applies(
    client, viewer_headers, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="research-pulse-order@example.com")
    for title, priority, last_touch_at in (
        ("Beta Focus", 5, "2026-04-19T09:00:00Z"),
        ("Alpha Focus", 5, "2026-04-19T09:00:00Z"),
        ("Gamma Focus", 4, "2026-04-19T08:00:00Z"),
    ):
        paper = create_paper(
            client,
            operator_headers,
            user_id=user["id"],
            title=title,
            stage="reviewing",
            priority=priority,
            identifiers={
                "doi": f"10.1000/{title.lower().replace(' ', '-')}",
                "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
                "import_authors": ["Alice Zhang"],
                "import_year": 2024,
                "progress_workbench": {"reading_status": "reading"},
            },
            next_action="继续推进阅读",
            last_touch_at=last_touch_at,
        )
        update_progress(
            client,
            operator_headers,
            paper_id=paper["id"],
            research_stage="reviewing",
            reading_status="reading",
            priority="urgent" if priority == 5 else "high",
            next_action="继续推进阅读",
        )

    first_payload = generate_pulse(
        client,
        viewer_headers,
        user_id=user["id"],
        max_items_per_section=2,
    )
    second_payload = generate_pulse(
        client,
        viewer_headers,
        user_id=user["id"],
        max_items_per_section=2,
    )

    first_titles = [item["title"] for item in section(first_payload, "today_focus")["items"]]
    second_titles = [item["title"] for item in section(second_payload, "today_focus")["items"]]

    assert len(first_titles) == 2
    assert first_titles == second_titles
    assert first_titles == ["Alpha Focus", "Beta Focus"]


def test_archived_and_low_priority_filters_behave_as_expected(
    client, viewer_headers, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="research-pulse-filters@example.com")

    archived = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Archived Important Paper",
        stage="reviewing",
        priority=5,
        identifiers={
            "doi": "10.1000/archived",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "archived"},
        },
        next_action="已归档但保留参考",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=archived["id"],
        research_stage="reviewing",
        reading_status="archived",
        priority="urgent",
        next_action="已归档但保留参考",
    )

    low_priority = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Low Priority Action Paper",
        stage="relevant",
        priority=1,
        identifiers={
            "doi": "10.1000/low",
            "import_source_format": PaperImportSourceFormat.RIS.value,
            "import_authors": ["Bo Li"],
            "import_year": 2022,
            "progress_workbench": {"reading_status": "reading"},
        },
        next_action="低优先级后续再看",
    )
    update_progress(
        client,
        operator_headers,
        paper_id=low_priority["id"],
        research_stage="relevant",
        reading_status="reading",
        priority="low",
        next_action="低优先级后续再看",
    )

    default_payload = generate_pulse(client, viewer_headers, user_id=user["id"])
    full_payload = generate_pulse(
        client,
        viewer_headers,
        user_id=user["id"],
        include_archived=True,
        include_low_priority=True,
    )

    default_focus_titles = {
        item["title"] for item in section(default_payload, "today_focus")["items"]
    }
    full_focus_titles = {item["title"] for item in section(full_payload, "today_focus")["items"]}
    default_action_titles = {
        item["title"] for item in section(default_payload, "next_actions")["items"]
    }
    full_action_titles = {item["title"] for item in section(full_payload, "next_actions")["items"]}

    assert "Archived Important Paper" not in default_focus_titles
    assert "Low Priority Action Paper" not in default_focus_titles
    assert "Archived Important Paper" in full_focus_titles
    assert "Low Priority Action Paper" in full_focus_titles
    assert "Archived Important Paper" not in default_action_titles
    assert "Archived Important Paper" in full_action_titles


def test_source_format_filter_and_imported_paper_commit_are_supported(
    client, viewer_headers, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="research-pulse-import@example.com")

    preview = client.post(
        "/papers/import-preview",
        headers=operator_headers,
        json={
            "source_format": PaperImportSourceFormat.CSL_JSON.value,
            "payload": [
                {
                    "title": "Imported Pulse Paper",
                    "author": [{"given": "Alice", "family": "Zhang"}],
                    "issued": {"date-parts": [[2026]]},
                    "container-title": "Import Journal",
                    "DOI": "10.1000/imported-pulse",
                }
            ],
        },
    )
    assert preview.status_code == 201

    committed = client.post(
        "/papers/import-commit",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "source_format": PaperImportSourceFormat.CSL_JSON.value,
            "preview_id": preview.json()["preview_id"],
            "preview_records": preview.json()["records"],
            "selected_source_indexes": [1],
        },
    )
    assert committed.status_code == 200
    paper_id = committed.json()["committed_record_ids"][0]
    update_progress(
        client,
        operator_headers,
        paper_id=paper_id,
        research_stage="inbox",
        reading_status="unread",
        priority="high",
    )

    create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Other Format Paper",
        stage="reviewing",
        priority=5,
        identifiers={
            "doi": "10.1000/other-format",
            "import_source_format": PaperImportSourceFormat.RIS.value,
            "import_authors": ["Other Author"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "reading"},
        },
        next_action="继续推进",
    )

    payload = generate_pulse(
        client,
        viewer_headers,
        user_id=user["id"],
        source_format_filter=[PaperImportSourceFormat.CSL_JSON.value],
    )

    titles = {
        item["title"]
        for section_payload in payload["sections"]
        for item in section_payload["items"]
    }
    assert "Imported Pulse Paper" in titles
    assert "Other Format Paper" not in titles
    assert payload["source_context_notes"]
