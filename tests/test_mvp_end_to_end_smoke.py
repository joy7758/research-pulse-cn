import json

from research_pulse_cn.db.models import DeliveryJob, DigestPublicationJob, PulseDigestIssue
from research_pulse_cn.domain.enums import (
    PaperImportSourceFormat,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def create_user(client, headers, *, email: str = "mvp-smoke@example.com") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "MVP Smoke User",
            "email": email,
            "field": "Materials",
            "interests": ["diffusion", "phase field"],
            "watched_topics": ["alloys"],
            "watched_venues": ["Acta Materialia", "Scripta Materialia"],
            "reminder_preferences": {"timezone": "Asia/Shanghai"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_binding(client, headers, *, user_id: str, openid: str = "mvp-smoke-openid") -> dict:
    response = client.post(
        "/admin/wechat-bindings",
        headers=headers,
        json={
            "user_id": user_id,
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-research-pulse-smoke",
            "openid": openid,
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Smoke 公众号",
        },
    )
    assert response.status_code == 201
    return response.json()


def build_tabular_payload() -> str:
    return (
        "标题\t作者\t发表年份\t来源\tdoi\t链接\t摘要\t关键词\n"
        "高优先级扩散模型论文\t张三；李四\t2025\tActa Materialia\t10.1000/focus-smoke\t"
        "https://example.local/focus\t扩散模型摘要\t重点；扩散\n"
        "继续阅读的材料论文\t王五\t2024\tScripta Materialia\t10.1000/reading-smoke\t"
        "https://example.local/reading\t继续阅读摘要\t阅读；方法\n"
        "待补全元数据论文\t\t\t\t\thttps://example.local/metadata\t\t补全\n"
        "新导入待筛选论文\t赵六\t2023\t材料导报\t10.1000/triage-smoke\t"
        "https://example.local/triage\t筛选摘要\t筛选；导入\n"
        "\t缺标题作者\t2022\t未知来源\t10.1000/invalid-smoke\thttps://example.local/invalid\t无效摘要\t错误\n"
    )


def update_progress(client, headers, *, paper_id: str, **payload) -> dict:
    response = client.patch(f"/papers/{paper_id}/progress", headers=headers, json=payload)
    assert response.status_code == 200
    return response.json()


def flatten_card_items(payload: dict) -> list[dict]:
    items: list[dict] = []
    for card in payload["cards"]:
        items.extend(card["items"])
    return items


def section(payload: dict, section_id: str) -> dict:
    return next(item for item in payload["sections"] if item["section_id"] == section_id)


def test_mvp_end_to_end_smoke_chain_from_import_to_multi_surface_drafts(
    client,
    session,
    operator_headers,
    viewer_headers,
) -> None:
    user = create_user(client, operator_headers)
    binding = create_binding(client, operator_headers, user_id=user["id"])

    preview_response = client.post(
        "/papers/import-preview",
        headers=operator_headers,
        json={
            "source_format": PaperImportSourceFormat.TABULAR.value,
            "payload": build_tabular_payload(),
        },
    )
    assert preview_response.status_code == 201
    preview_payload = preview_response.json()

    assert preview_payload["total_records"] == 5
    assert preview_payload["valid_records_count"] == 4
    assert preview_payload["error_records_count"] == 1
    assert preview_payload["records"][-1]["can_commit"] is False
    assert {problem["code"] for problem in preview_payload["records"][-1]["errors"]} == {
        "missing_required_field"
    }

    commit_response = client.post(
        "/papers/import-commit",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "source_format": PaperImportSourceFormat.TABULAR.value,
            "preview_id": preview_payload["preview_id"],
            "preview_records": preview_payload["records"],
            "selected_source_indexes": [1, 2, 3, 4, 5],
        },
    )
    assert commit_response.status_code == 200
    commit_payload = commit_response.json()

    assert commit_payload["total_selected"] == 5
    assert commit_payload["committed_count"] == 4
    assert commit_payload["skipped_count"] == 1
    assert commit_payload["failed_count"] == 0

    committed_by_index = {
        item["source_index"]: item["paper_id"]
        for item in commit_payload["record_results"]
        if item["status"] == "committed"
    }
    skipped = next(item for item in commit_payload["record_results"] if item["status"] == "skipped")
    assert skipped["source_index"] == 5
    assert skipped["reason"] == "record is not importable"

    focus_paper_id = committed_by_index[1]
    reading_paper_id = committed_by_index[2]
    metadata_paper_id = committed_by_index[3]
    triage_paper_id = committed_by_index[4]

    focus_progress = update_progress(
        client,
        operator_headers,
        paper_id=focus_paper_id,
        reading_status="reading",
        research_stage="reviewing",
        priority="urgent",
        next_action="先整理方法对比表",
        user_note="今天优先推进。",
        tags=["重点", "扩散"],
    )
    reading_progress = update_progress(
        client,
        operator_headers,
        paper_id=reading_paper_id,
        reading_status="skimming",
        research_stage="relevant",
        priority="normal",
        clear_next_action=True,
        research_note="先扫读方法和实验设置。",
        tags=["阅读中"],
    )
    metadata_progress = update_progress(
        client,
        operator_headers,
        paper_id=metadata_paper_id,
        reading_status="unread",
        research_stage="inbox",
        priority="high",
        clear_next_action=True,
        tags=["待补全"],
    )
    triage_progress = update_progress(
        client,
        operator_headers,
        paper_id=triage_paper_id,
        reading_status="unread",
        research_stage="triage",
        priority="normal",
        clear_next_action=True,
        tags=["待筛选"],
    )

    assert focus_progress["next_action"] == "先整理方法对比表"
    assert reading_progress["research_stage"] == "relevant"
    assert metadata_progress["priority"] == "high"
    assert triage_progress["reading_status"] == "unread"

    progress_list = client.get(
        "/papers/progress",
        headers=viewer_headers,
        params={"user_id": user["id"]},
    )
    summary_response = client.get(
        "/papers/progress/summary",
        headers=viewer_headers,
        params={"user_id": user["id"]},
    )
    pulse_context = client.get(
        "/papers/progress/pulse-context",
        headers=viewer_headers,
        params={"user_id": user["id"], "limit": 10},
    )

    assert progress_list.status_code == 200
    assert summary_response.status_code == 200
    assert pulse_context.status_code == 200

    progress_payload = progress_list.json()
    summary_payload = summary_response.json()
    context_payload = pulse_context.json()

    assert progress_payload["total_items"] == 4
    assert summary_payload["total_papers"] == 4
    assert summary_payload["unread_count"] == 2
    assert summary_payload["reading_count"] == 2
    assert summary_payload["read_count"] == 0
    assert summary_payload["high_priority_count"] == 1
    assert summary_payload["urgent_count"] == 1
    assert summary_payload["with_next_action_count"] == 1
    assert summary_payload["by_research_stage"]["reviewing"] == 1
    assert summary_payload["by_research_stage"]["triage"] == 1
    assert summary_payload["by_priority"]["urgent"] == 1
    assert context_payload["high_priority_papers"]
    assert context_payload["papers_with_next_action"][0]["paper_id"] == focus_paper_id
    assert context_payload["metadata_attention_papers"]

    pulse_response = client.post(
        "/pulse/papers/daily",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "timezone": "Asia/Shanghai",
            "max_items_per_section": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "dry_run": True,
        },
    )
    assert pulse_response.status_code == 200
    pulse_payload = pulse_response.json()

    today_focus = section(pulse_payload, "today_focus")
    continue_reading = section(pulse_payload, "continue_reading")
    next_actions = section(pulse_payload, "next_actions")
    metadata_attention = section(pulse_payload, "metadata_attention")
    triage_section = section(pulse_payload, "newly_imported_triage")

    assert pulse_payload["total_source_papers"] == 4
    assert pulse_payload["dry_run"] is True
    assert pulse_payload["title"].endswith("科研 Pulse 草稿")
    assert "今日已从" in pulse_payload["summary"]
    assert today_focus["items"][0]["paper_id"] == focus_paper_id
    assert any(item["paper_id"] == reading_paper_id for item in continue_reading["items"])
    assert next_actions["items"][0]["paper_id"] == focus_paper_id
    assert any(item["paper_id"] == metadata_paper_id for item in metadata_attention["items"])
    assert any(item["paper_id"] == triage_paper_id for item in triage_section["items"])
    assert today_focus["items"][0]["reason"]
    assert today_focus["items"][0]["suggested_action"] == "先整理方法对比表"
    assert "摘要" not in today_focus["items"][0]["reason"]

    assert session.query(PulseDigestIssue).count() == 0
    assert session.query(DigestPublicationJob).count() == 0
    official_response = client.post(
        "/pulse/papers/official-account/daily-summary",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "timezone": "Asia/Shanghai",
            "max_items_per_section": 3,
            "max_highlights": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "binding_id": binding["id"],
            "dry_run": True,
        },
    )
    assert official_response.status_code == 200
    official_payload = official_response.json()

    assert official_payload["dry_run"] is True
    assert official_payload["title"].endswith("公众号每日摘要草稿")
    assert official_payload["publication_preview"]["digest_title"]
    assert official_payload["binding_preview"]["selected_binding"]["binding_id"] == binding["id"]
    assert "已发送成功" not in json.dumps(official_payload, ensure_ascii=False)
    session.expire_all()
    assert session.query(PulseDigestIssue).count() == 0
    assert session.query(DigestPublicationJob).count() == 0

    assert session.query(DeliveryJob).count() == 0
    desktop_response = client.post(
        "/pulse/papers/desktop-notification/draft",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "timezone": "Asia/Shanghai",
            "max_items": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "title_prefix": "今日科研 Pulse",
            "include_actions": True,
            "dry_run": True,
        },
    )
    assert desktop_response.status_code == 200
    desktop_payload = desktop_response.json()

    assert desktop_payload["delivery_state"] == "draft"
    assert desktop_payload["deep_link"].startswith("research-pulse://pulse/daily/")
    assert desktop_payload["payload_preview"]["delivery_state"] == "draft"
    assert desktop_payload["urgency"] == "high"
    assert desktop_payload["badge_count"] >= 2
    assert any(item["paper_id"] == focus_paper_id for item in desktop_payload["items"])
    assert {action["label"] for action in desktop_payload["actions"]} >= {
        "查看今日 Pulse",
        "查看下一步动作",
        "补全元数据",
        "筛选新导入论文",
    }
    assert "已推送成功" not in json.dumps(desktop_payload, ensure_ascii=False)
    session.expire_all()
    assert session.query(DeliveryJob).count() == 0

    mini_daily_response = client.post(
        "/pulse/papers/mini-program/detail/preview",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "detail_type": "daily_pulse",
            "pulse_date": pulse_payload["pulse_date"],
            "source_research_pulse_draft_id": pulse_payload["draft_id"],
            "timezone": "Asia/Shanghai",
            "max_items": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "share_safe": True,
            "dry_run": True,
        },
    )
    assert mini_daily_response.status_code == 200
    mini_daily_payload = mini_daily_response.json()

    assert mini_daily_payload["delivery_state"] == "preview"
    assert mini_daily_payload["share_card"]["share_safe"] is True
    assert mini_daily_payload["navigation"]["current_path"].startswith("/pages/pulse/detail?date=")
    assert (
        mini_daily_payload["share_card"]["path"] == mini_daily_payload["navigation"]["current_path"]
    )
    assert any(card["card_type"] == "today_focus" for card in mini_daily_payload["cards"])

    mini_paper_response = client.post(
        "/pulse/papers/mini-program/detail/preview",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "detail_type": "paper",
            "paper_id": metadata_paper_id,
            "timezone": "Asia/Shanghai",
            "max_items": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "share_safe": True,
            "dry_run": True,
        },
    )
    assert mini_paper_response.status_code == 200
    mini_paper_payload = mini_paper_response.json()
    paper_items = flatten_card_items(mini_paper_payload)

    assert mini_paper_payload["delivery_state"] == "preview"
    assert mini_paper_payload["navigation"]["current_path"].startswith("/pages/papers/detail?id=")
    assert any(item["paper_id"] == metadata_paper_id for item in paper_items)

    mini_next_response = client.post(
        "/pulse/papers/mini-program/detail/preview",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "detail_type": "next_actions",
            "timezone": "Asia/Shanghai",
            "max_items": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "share_safe": True,
            "dry_run": True,
        },
    )
    assert mini_next_response.status_code == 200
    mini_next_payload = mini_next_response.json()
    assert any(item["paper_id"] == focus_paper_id for item in flatten_card_items(mini_next_payload))

    mini_metadata_response = client.post(
        "/pulse/papers/mini-program/detail/preview",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "detail_type": "metadata_attention",
            "timezone": "Asia/Shanghai",
            "max_items": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "share_safe": True,
            "dry_run": True,
        },
    )
    assert mini_metadata_response.status_code == 200
    mini_metadata_payload = mini_metadata_response.json()
    mini_metadata_dump = json.dumps(mini_metadata_payload, ensure_ascii=False)
    assert any(
        item["paper_id"] == metadata_paper_id for item in flatten_card_items(mini_metadata_payload)
    )
    assert "raw_source_payload" not in mini_metadata_dump
    assert "import_raw_source_payload" not in mini_metadata_dump
    assert "user_note" not in mini_metadata_dump
    assert "research_note" not in mini_metadata_dump

    mini_triage_response = client.post(
        "/pulse/papers/mini-program/detail/preview",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "detail_type": "triage",
            "timezone": "Asia/Shanghai",
            "max_items": 3,
            "include_low_priority": False,
            "include_archived": False,
            "source_format_filter": [],
            "share_safe": True,
            "dry_run": True,
        },
    )
    assert mini_triage_response.status_code == 200
    mini_triage_payload = mini_triage_response.json()
    assert any(
        item["paper_id"] == triage_paper_id for item in flatten_card_items(mini_triage_payload)
    )
