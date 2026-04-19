from research_pulse_cn.domain.enums import PaperImportSourceFormat, PaperType


def create_user(client, headers, *, email: str = "progress-user@example.com") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Progress User",
            "email": email,
            "field": "Materials",
            "interests": ["alloys"],
            "watched_topics": ["diffusion"],
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
        },
    )
    assert response.status_code == 201
    return response.json()


def test_progress_list_and_detail_are_built_from_paper_profile(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="progress-list@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Imported Alloy Study",
        stage="imported",
        priority=4,
        identifiers={
            "doi": "10.1000/alloy-progress",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang", "Bo Li"],
            "import_keywords": ["alloy", "diffusion"],
            "import_year": 2024,
        },
        next_action="Review imported paper metadata",
    )

    listed = client.get(
        "/papers/progress", headers=operator_headers, params={"user_id": user["id"]}
    )
    detail = client.get(f"/papers/{paper['id']}/progress", headers=operator_headers)

    assert listed.status_code == 200
    assert detail.status_code == 200

    list_payload = listed.json()
    item = list_payload["items"][0]
    assert list_payload["total_items"] == 1
    assert item["paper_id"] == paper["id"]
    assert item["reading_status"] == "unread"
    assert item["research_stage"] == "inbox"
    assert item["priority"] == "high"
    assert item["source_format"] == "csl_json"
    assert item["authors"] == ["Alice Zhang", "Bo Li"]
    assert item["year"] == 2024
    assert item["tags"] == ["alloy", "diffusion"]
    assert detail.json()["paper_id"] == paper["id"]


def test_progress_patch_updates_status_priority_notes_and_next_action(
    client, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="progress-update@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Workbench Update Paper",
        stage="imported",
    )

    patched = client.patch(
        f"/papers/{paper['id']}/progress",
        headers=operator_headers,
        json={
            "reading_status": "reading",
            "research_stage": "reviewing",
            "priority": "urgent",
            "next_action": "Extract key baseline comparison results",
            "user_note": "导师要求优先处理这篇。",
            "research_note": "重点关注实验设置和数据切分方式。",
            "tags": ["high-temp", "baseline"],
        },
    )
    cleared = client.patch(
        f"/papers/{paper['id']}/progress",
        headers=operator_headers,
        json={"clear_next_action": True},
    )
    raw_paper = client.get(f"/papers/{paper['id']}", headers=operator_headers)

    assert patched.status_code == 200
    patched_payload = patched.json()
    assert patched_payload["reading_status"] == "reading"
    assert patched_payload["research_stage"] == "reviewing"
    assert patched_payload["priority"] == "urgent"
    assert patched_payload["next_action"] == "Extract key baseline comparison results"
    assert patched_payload["user_note"] == "导师要求优先处理这篇。"
    assert patched_payload["research_note"] == "重点关注实验设置和数据切分方式。"
    assert patched_payload["tags"] == ["high-temp", "baseline"]

    assert cleared.status_code == 200
    assert cleared.json()["next_action"] is None

    assert raw_paper.status_code == 200
    raw_payload = raw_paper.json()
    assert raw_payload["stage"] == "reviewing"
    assert raw_payload["priority"] == 5
    assert raw_payload["next_action"] is None
    assert raw_payload["identifiers"]["progress_workbench"]["reading_status"] == "reading"
    assert raw_payload["identifiers"]["progress_workbench"]["user_note"] == "导师要求优先处理这篇。"
    assert raw_payload["identifiers"]["progress_workbench"]["research_note"] == (
        "重点关注实验设置和数据切分方式。"
    )
    assert raw_payload["identifiers"]["progress_workbench"]["tags"] == ["high-temp", "baseline"]


def test_invalid_progress_status_returns_validation_error(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="progress-invalid@example.com")
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Invalid Status Paper")

    response = client.patch(
        f"/papers/{paper['id']}/progress",
        headers=operator_headers,
        json={"reading_status": "deep_reading"},
    )

    assert response.status_code == 422


def test_progress_summary_and_filters_cover_status_stage_priority_and_next_action(
    client, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="progress-summary@example.com")
    create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Unread Inbox Paper",
        stage="inbox",
        priority=1,
        identifiers={
            "import_source_format": PaperImportSourceFormat.TABULAR.value,
            "import_authors": ["Zhang San"],
            "import_keywords": ["表格导入"],
            "import_year": 2022,
            "progress_workbench": {"reading_status": "unread"},
        },
    )
    create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Reading Review Paper",
        stage="reviewing",
        priority=4,
        identifiers={
            "doi": "10.1000/reviewing",
            "import_source_format": PaperImportSourceFormat.BIBTEX.value,
            "import_authors": ["Alice Zhang"],
            "import_year": 2024,
            "progress_workbench": {
                "reading_status": "reading",
                "tags": ["diffusion", "关键论文"],
            },
        },
        next_action="Compare methods section",
    )
    create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Read Cited Paper",
        stage="cited",
        priority=5,
        identifiers={
            "doi": "10.1000/cited",
            "import_source_format": PaperImportSourceFormat.RIS.value,
            "import_authors": ["Bo Li"],
            "import_year": 2023,
            "progress_workbench": {"reading_status": "read"},
        },
        next_action="Add citation note",
    )

    summary = client.get(
        "/papers/progress/summary",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    reading_filtered = client.get(
        "/papers/progress",
        headers=operator_headers,
        params={"user_id": user["id"], "reading_status": "reading"},
    )
    urgent_filtered = client.get(
        "/papers/progress",
        headers=operator_headers,
        params={"user_id": user["id"], "priority": "urgent"},
    )
    action_filtered = client.get(
        "/papers/progress",
        headers=operator_headers,
        params={"user_id": user["id"], "has_next_action": "true"},
    )
    keyword_filtered = client.get(
        "/papers/progress",
        headers=operator_headers,
        params={"user_id": user["id"], "keyword": "关键论文"},
    )

    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["total_papers"] == 3
    assert summary_payload["unread_count"] == 1
    assert summary_payload["reading_count"] == 1
    assert summary_payload["read_count"] == 1
    assert summary_payload["high_priority_count"] == 1
    assert summary_payload["urgent_count"] == 1
    assert summary_payload["with_next_action_count"] == 2
    assert summary_payload["by_reading_status"]["reading"] == 1
    assert summary_payload["by_research_stage"]["reviewing"] == 1
    assert summary_payload["by_priority"]["urgent"] == 1

    assert reading_filtered.status_code == 200
    assert reading_filtered.json()["total_items"] == 1
    assert reading_filtered.json()["items"][0]["title"] == "Reading Review Paper"

    assert urgent_filtered.status_code == 200
    assert urgent_filtered.json()["total_items"] == 1
    assert urgent_filtered.json()["items"][0]["title"] == "Read Cited Paper"

    assert action_filtered.status_code == 200
    assert action_filtered.json()["total_items"] == 2

    assert keyword_filtered.status_code == 200
    assert keyword_filtered.json()["total_items"] == 1
    assert keyword_filtered.json()["items"][0]["title"] == "Reading Review Paper"


def test_import_commit_records_are_compatible_with_progress_workbench(
    client, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="progress-import@example.com")

    preview = client.post(
        "/papers/import-preview",
        headers=operator_headers,
        json={
            "source_format": PaperImportSourceFormat.CSL_JSON.value,
            "payload": [
                {
                    "title": "Imported Progress Paper",
                    "author": [{"given": "Alice", "family": "Zhang"}],
                    "issued": {"date-parts": [[2025]]},
                    "container-title": "Import Journal",
                    "DOI": "10.1000/imported-progress",
                    "keyword": "合金;研究脉冲",
                }
            ],
        },
    )
    assert preview.status_code == 201
    preview_payload = preview.json()

    committed = client.post(
        "/papers/import-commit",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "source_format": PaperImportSourceFormat.CSL_JSON.value,
            "preview_id": preview_payload["preview_id"],
            "preview_records": preview_payload["records"],
            "selected_source_indexes": [1],
        },
    )
    assert committed.status_code == 200
    paper_id = committed.json()["committed_record_ids"][0]

    progress_list = client.get(
        "/papers/progress",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    progress_detail = client.get(f"/papers/{paper_id}/progress", headers=operator_headers)

    assert progress_list.status_code == 200
    assert progress_detail.status_code == 200
    item = progress_list.json()["items"][0]
    assert item["paper_id"] == paper_id
    assert item["source_format"] == "csl_json"
    assert item["research_stage"] == "inbox"
    assert item["year"] == 2025
    assert item["authors"] == ["Alice Zhang"]
    assert item["next_action"] == "Review imported paper metadata"


def test_pulse_context_returns_high_priority_next_action_review_and_metadata_attention(
    client, operator_headers
) -> None:
    user = create_user(client, operator_headers, email="progress-pulse@example.com")
    create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Urgent With Action",
        stage="reviewing",
        priority=5,
        identifiers={
            "doi": "10.1000/urgent-action",
            "import_source_format": PaperImportSourceFormat.CSL_JSON.value,
            "import_authors": ["Alice Zhang"],
            "import_year": 2024,
            "progress_workbench": {"reading_status": "reading"},
        },
        next_action="Write comparison note",
    )
    create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Metadata Gap PDF",
        stage="inbox",
        priority=4,
        venue=None,
        identifiers={
            "import_source_format": PaperImportSourceFormat.PDF_FOLDER.value,
            "progress_workbench": {"reading_status": "skimming"},
        },
    )

    context = client.get(
        "/papers/progress/pulse-context",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )

    assert context.status_code == 200
    payload = context.json()
    assert payload["high_priority_papers"][0]["title"] == "Urgent With Action"
    assert payload["papers_with_next_action"][0]["title"] == "Urgent With Action"
    titles_in_active_review = {item["title"] for item in payload["active_review_papers"]}
    assert titles_in_active_review == {"Urgent With Action", "Metadata Gap PDF"}
    titles_in_metadata_attention = {item["title"] for item in payload["metadata_attention_papers"]}
    assert "Metadata Gap PDF" in titles_in_metadata_attention
    assert payload["notes"]
