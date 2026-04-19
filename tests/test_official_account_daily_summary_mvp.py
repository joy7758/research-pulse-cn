from datetime import UTC, datetime
from uuid import uuid4

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import DigestPublicationJob, PulseDigestIssue
from research_pulse_cn.domain.enums import (
    PaperImportSourceFormat,
    PaperType,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def create_user(client, headers, *, email: str = "official-daily-summary@example.com") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Official Summary User",
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


def create_binding(client, headers, *, user_id: str, openid: str = "openid-123456") -> dict:
    response = client.post(
        "/admin/wechat-bindings",
        headers=headers,
        json={
            "user_id": user_id,
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": openid,
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "主公众号",
        },
    )
    assert response.status_code == 201
    return response.json()


def generate_daily_summary(client, headers, *, user_id: str, **overrides) -> dict:
    payload = {
        "user_id": user_id,
        "timezone": "Asia/Shanghai",
        "max_items_per_section": 3,
        "max_highlights": 3,
        "include_low_priority": False,
        "include_archived": False,
        "source_format_filter": [],
        "dry_run": True,
    }
    payload.update(overrides)
    response = client.post(
        "/pulse/papers/official-account/daily-summary",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def summary_section(payload: dict, section_id: str) -> dict:
    return next(item for item in payload["sections"] if item["section_id"] == section_id)


def test_official_account_daily_summary_handles_empty_library_without_persistence(
    client,
    viewer_headers,
    operator_headers,
    session,
) -> None:
    user = create_user(client, operator_headers, email="official-empty@example.com")

    assert session.query(PulseDigestIssue).count() == 0
    assert session.query(DigestPublicationJob).count() == 0

    payload = generate_daily_summary(client, viewer_headers, user_id=user["id"])

    assert payload["highlight_count"] == 0
    assert payload["binding_preview"]["active_binding_count"] == 0
    assert payload["publication_preview"]["primary_cta_path"] == "/mini/today"
    assert payload["template_payload_preview"]["payload_preview"]["data"]
    assert payload["warnings"]
    assert summary_section(payload, "today_focus")["empty_reason"]

    session.expire_all()
    assert session.query(PulseDigestIssue).count() == 0
    assert session.query(DigestPublicationJob).count() == 0


def test_official_account_daily_summary_builds_highlights_and_template_payload_preview(
    client,
    viewer_headers,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID", "tmpl-daily-summary")
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID", "wx-mini-app")
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL", "https://mp.example.cn")
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON",
        '{"issue_title":"first","issue_date":"keyword1","highlight_count":"keyword2","summary":"keyword3","remark":"remark"}',
    )
    get_settings.cache_clear()

    user = create_user(client, operator_headers, email="official-highlights@example.com")
    binding = create_binding(client, operator_headers, user_id=user["id"])

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

    payload = generate_daily_summary(
        client,
        viewer_headers,
        user_id=user["id"],
        binding_id=binding["id"],
        max_highlights=2,
    )

    assert payload["binding_preview"]["active_binding_count"] == 1
    assert payload["binding_preview"]["selected_binding"]["binding_id"] == binding["id"]
    assert payload["publication_preview"]["article_url"] == "https://mp.example.cn/mini/today"
    assert payload["publication_preview"]["mini_program_path"] == "mini/today"
    assert len(payload["publication_preview"]["digest_highlights"]) == 2
    assert payload["template_payload_preview"]["template_id_configured"] is True
    assert payload["template_payload_preview"]["payload_preview"]["binding_id"] == binding["id"]
    assert (
        payload["template_payload_preview"]["payload_preview"]["miniprogram"]["appid"]
        == "wx-mini-app"
    )
    assert payload["template_payload_preview"]["field_mapping"]["issue_title"] == "first"
    assert summary_section(payload, "today_focus")["items"][0]["title"] == "Urgent Focus Paper"
    assert {item["title"] for item in summary_section(payload, "metadata_attention")["items"]} >= {
        "Metadata Gap PDF"
    }
    assert {
        item["title"] for item in summary_section(payload, "newly_imported_triage")["items"]
    } >= {
        "Metadata Gap PDF",
        "New Triage Paper",
    }

    session.expire_all()
    assert session.query(PulseDigestIssue).count() == 0
    assert session.query(DigestPublicationJob).count() == 0


def test_official_account_daily_summary_excludes_archived_by_default_and_can_include_them(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="official-archived@example.com")
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
            "import_year": 2024,
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

    excluded = generate_daily_summary(client, viewer_headers, user_id=user["id"])
    included = generate_daily_summary(
        client,
        viewer_headers,
        user_id=user["id"],
        include_archived=True,
    )

    assert excluded["total_source_papers"] == 0
    assert excluded["highlight_count"] == 0
    assert included["total_source_papers"] == 1
    assert included["highlight_count"] == 1
    assert (
        included["publication_preview"]["digest_highlights"][0]["title"] == "Archived Focus Paper"
    )


def test_official_account_daily_summary_returns_not_found_for_missing_active_binding(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="official-binding-missing@example.com")
    create_binding(client, operator_headers, user_id=user["id"], openid="openid-live")

    response = client.post(
        "/pulse/papers/official-account/daily-summary",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "binding_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
