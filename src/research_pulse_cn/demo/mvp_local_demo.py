"""Local offline MVP demo runner for fixture-based walkthroughs."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from research_pulse_cn.app import create_app
from research_pulse_cn.auth.crypto import hash_password
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.db.base import Base
from research_pulse_cn.db.models import AdminAccount
from research_pulse_cn.db.session import get_engine, get_session_factory, reset_db_session_state
from research_pulse_cn.domain.enums import (
    AdminRole,
    PaperImportSourceFormat,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.services.official_account import reset_official_account_runtime_state

_FIXTURE_FILE_BY_FORMAT: dict[str, tuple[str, PaperImportSourceFormat]] = {
    "csv": ("demo_papers_cn.csv", PaperImportSourceFormat.TABULAR),
    "csl": ("demo_papers_csl.json", PaperImportSourceFormat.CSL_JSON),
    "bibtex": ("demo_papers.bib", PaperImportSourceFormat.BIBTEX),
    "ris": ("demo_papers.ris", PaperImportSourceFormat.RIS),
    "pdf_manifest": ("demo_pdf_folder_manifest.json", PaperImportSourceFormat.PDF_FOLDER),
}

_OUTPUT_FILE_NAMES = {
    "import_preview": "import_preview.json",
    "import_commit": "import_commit.json",
    "paper_progress_summary": "paper_progress_summary.json",
    "research_pulse": "research_pulse.json",
    "official_account_daily_summary": "official_account_daily_summary.json",
    "desktop_notification": "desktop_notification.json",
    "mini_program_daily_pulse_detail": "mini_program_daily_pulse_detail.json",
    "mini_program_paper_detail": "mini_program_paper_detail.json",
    "mini_program_next_actions_detail": "mini_program_next_actions_detail.json",
    "mini_program_metadata_attention_detail": "mini_program_metadata_attention_detail.json",
    "mini_program_triage_detail": "mini_program_triage_detail.json",
    "demo_summary": "demo_summary.md",
}

_DEMO_USER_PAYLOAD = {
    "name": "本地演示用户",
    "email": "demo-user@example.com",
    "field": "科研产品设计",
    "interests": ["论文管理", "科研进度", "知识组织"],
    "watched_topics": ["Research Pulse", "科研协同"],
    "watched_venues": ["科研协同学刊", "教育技术研究"],
    "reminder_preferences": {"timezone": "Asia/Shanghai"},
    "risk_thresholds": {"stalled_days": 14},
}

_PROGRESS_UPDATES_BY_SOURCE_INDEX: dict[int, dict[str, Any]] = {
    1: {
        "reading_status": "reading",
        "research_stage": "reviewing",
        "priority": "urgent",
        "next_action": "今天先整理方法差异和实验变量",
        "user_note": "这是本轮演示里的今日重点论文。",
        "tags": ["重点", "今日推进"],
    },
    2: {
        "reading_status": "skimming",
        "research_stage": "relevant",
        "priority": "normal",
        "clear_next_action": True,
        "research_note": "适合放进继续阅读与分析 section。",
        "tags": ["继续阅读"],
    },
    3: {
        "reading_status": "unread",
        "research_stage": "inbox",
        "priority": "high",
        "clear_next_action": True,
        "tags": ["待补全"],
    },
    4: {
        "reading_status": "unread",
        "research_stage": "triage",
        "priority": "normal",
        "clear_next_action": True,
        "tags": ["待筛选"],
    },
    5: {
        "reading_status": "read",
        "research_stage": "cited",
        "priority": "normal",
        "next_action": "下次汇报时引用这篇结论部分",
        "tags": ["已读", "已引用"],
    },
    6: {
        "reading_status": "archived",
        "research_stage": "parked",
        "priority": "low",
        "clear_next_action": True,
        "tags": ["低优先级", "暂缓"],
    },
}

_ENV_KEYS = (
    "APP_ENV",
    "APP_LOG_LEVEL",
    "APP_DATABASE_URL",
    "APP_MAX_DELIVERY_RETRIES",
    "APP_DELIVERY_RETRY_DELAY_SECONDS",
    "APP_AUTH_JWT_SECRET",
    "APP_AUTH_JWT_ISSUER",
    "APP_AUTH_JWT_AUDIENCE",
    "APP_INTERNAL_SERVICE_TOKEN",
)


@dataclass(slots=True)
class DemoRunResult:
    """Structured local demo outputs for tests, docs, and CLI rendering."""

    output_dir: Path
    import_preview: dict[str, Any]
    import_commit: dict[str, Any]
    paper_progress_summary: dict[str, Any]
    research_pulse: dict[str, Any]
    official_account_daily_summary: dict[str, Any]
    desktop_notification: dict[str, Any]
    mini_program_daily_pulse_detail: dict[str, Any]
    mini_program_paper_detail: dict[str, Any]
    mini_program_next_actions_detail: dict[str, Any]
    mini_program_metadata_attention_detail: dict[str, Any]
    mini_program_triage_detail: dict[str, Any]
    demo_summary_markdown: str
    selected_format: str
    fixture_file: str
    pulse_date: str


def available_fixture_formats() -> list[str]:
    """Return supported fixture format keys for CLI validation and docs."""

    return list(_FIXTURE_FILE_BY_FORMAT)


def run_mvp_demo(
    *,
    fixture_dir: Path,
    output_dir: Path,
    format_name: str = "csv",
    pulse_date: date | None = None,
    max_items_per_section: int = 3,
) -> DemoRunResult:
    """Run the full MVP chain locally and write deterministic demo artifacts."""

    if format_name not in _FIXTURE_FILE_BY_FORMAT:
        supported = ", ".join(available_fixture_formats())
        raise ValueError(f"unsupported demo format: {format_name}; supported: {supported}")

    fixture_file_name, source_format = _FIXTURE_FILE_BY_FORMAT[format_name]
    fixture_path = fixture_dir / fixture_file_name
    if not fixture_path.exists():
        raise FileNotFoundError(f"demo fixture file was not found: {fixture_path}")

    resolved_date = pulse_date or date(2026, 4, 19)
    output_dir.mkdir(parents=True, exist_ok=True)

    with _isolated_demo_environment():
        with TestClient(create_app()) as client:
            operator_headers, viewer_headers = _prepare_admin_access(client)
            user = _create_demo_user(client, operator_headers)
            binding = _create_demo_binding(client, operator_headers, user_id=user["id"])

            payload = _load_fixture_payload(fixture_path, format_name=format_name)
            import_preview = _request_json(
                client.post(
                    "/papers/import-preview",
                    headers=operator_headers,
                    json={
                        "source_format": source_format.value,
                        "payload": payload,
                    },
                )
            )
            import_commit = _request_json(
                client.post(
                    "/papers/import-commit",
                    headers=operator_headers,
                    json={
                        "user_id": user["id"],
                        "source_format": source_format.value,
                        "preview_id": import_preview["preview_id"],
                        "preview_records": import_preview["records"],
                        "selected_source_indexes": [
                            record["source_index"] for record in import_preview["records"]
                        ],
                    },
                )
            )

            committed_by_source_index = {
                item["source_index"]: item["paper_id"]
                for item in import_commit["record_results"]
                if item["status"] == "committed"
            }
            _apply_demo_progress_updates(
                client,
                operator_headers,
                committed_by_source_index=committed_by_source_index,
            )

            paper_progress_summary = _request_json(
                client.get(
                    "/papers/progress/summary",
                    headers=viewer_headers,
                    params={"user_id": user["id"]},
                )
            )
            research_pulse = _request_json(
                client.post(
                    "/pulse/papers/daily",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "pulse_date": resolved_date.isoformat(),
                        "timezone": "Asia/Shanghai",
                        "max_items_per_section": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "dry_run": True,
                    },
                )
            )
            official_account_daily_summary = _request_json(
                client.post(
                    "/pulse/papers/official-account/daily-summary",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "pulse_date": resolved_date.isoformat(),
                        "timezone": "Asia/Shanghai",
                        "max_items_per_section": max_items_per_section,
                        "max_highlights": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "binding_id": binding["id"],
                        "dry_run": True,
                    },
                )
            )
            desktop_notification = _request_json(
                client.post(
                    "/pulse/papers/desktop-notification/draft",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "pulse_date": resolved_date.isoformat(),
                        "timezone": "Asia/Shanghai",
                        "max_items": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "title_prefix": "今日科研 Pulse",
                        "include_actions": True,
                        "dry_run": True,
                    },
                )
            )

            metadata_paper_id = committed_by_source_index.get(3)
            mini_program_daily_pulse_detail = _request_json(
                client.post(
                    "/pulse/papers/mini-program/detail/preview",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "detail_type": "daily_pulse",
                        "pulse_date": research_pulse["pulse_date"],
                        "source_research_pulse_draft_id": research_pulse["draft_id"],
                        "timezone": "Asia/Shanghai",
                        "max_items": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "share_safe": True,
                        "dry_run": True,
                    },
                )
            )
            mini_program_paper_detail = _request_json(
                client.post(
                    "/pulse/papers/mini-program/detail/preview",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "detail_type": "paper",
                        "paper_id": metadata_paper_id,
                        "timezone": "Asia/Shanghai",
                        "max_items": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "share_safe": True,
                        "dry_run": True,
                    },
                )
            )
            mini_program_next_actions_detail = _request_json(
                client.post(
                    "/pulse/papers/mini-program/detail/preview",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "detail_type": "next_actions",
                        "timezone": "Asia/Shanghai",
                        "max_items": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "share_safe": True,
                        "dry_run": True,
                    },
                )
            )
            mini_program_metadata_attention_detail = _request_json(
                client.post(
                    "/pulse/papers/mini-program/detail/preview",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "detail_type": "metadata_attention",
                        "timezone": "Asia/Shanghai",
                        "max_items": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "share_safe": True,
                        "dry_run": True,
                    },
                )
            )
            mini_program_triage_detail = _request_json(
                client.post(
                    "/pulse/papers/mini-program/detail/preview",
                    headers=viewer_headers,
                    json={
                        "user_id": user["id"],
                        "detail_type": "triage",
                        "timezone": "Asia/Shanghai",
                        "max_items": max_items_per_section,
                        "include_low_priority": False,
                        "include_archived": False,
                        "source_format_filter": [],
                        "share_safe": True,
                        "dry_run": True,
                    },
                )
            )

    _write_json(output_dir / _OUTPUT_FILE_NAMES["import_preview"], import_preview)
    _write_json(output_dir / _OUTPUT_FILE_NAMES["import_commit"], import_commit)
    _write_json(output_dir / _OUTPUT_FILE_NAMES["paper_progress_summary"], paper_progress_summary)
    _write_json(output_dir / _OUTPUT_FILE_NAMES["research_pulse"], research_pulse)
    _write_json(
        output_dir / _OUTPUT_FILE_NAMES["official_account_daily_summary"],
        official_account_daily_summary,
    )
    _write_json(output_dir / _OUTPUT_FILE_NAMES["desktop_notification"], desktop_notification)
    _write_json(
        output_dir / _OUTPUT_FILE_NAMES["mini_program_daily_pulse_detail"],
        mini_program_daily_pulse_detail,
    )
    _write_json(
        output_dir / _OUTPUT_FILE_NAMES["mini_program_paper_detail"],
        mini_program_paper_detail,
    )
    _write_json(
        output_dir / _OUTPUT_FILE_NAMES["mini_program_next_actions_detail"],
        mini_program_next_actions_detail,
    )
    _write_json(
        output_dir / _OUTPUT_FILE_NAMES["mini_program_metadata_attention_detail"],
        mini_program_metadata_attention_detail,
    )
    _write_json(
        output_dir / _OUTPUT_FILE_NAMES["mini_program_triage_detail"],
        mini_program_triage_detail,
    )

    demo_summary_markdown = _build_demo_summary_markdown(
        import_preview=import_preview,
        import_commit=import_commit,
        paper_progress_summary=paper_progress_summary,
        research_pulse=research_pulse,
        official_account_daily_summary=official_account_daily_summary,
        desktop_notification=desktop_notification,
        mini_program_daily_pulse_detail=mini_program_daily_pulse_detail,
        mini_program_next_actions_detail=mini_program_next_actions_detail,
        mini_program_metadata_attention_detail=mini_program_metadata_attention_detail,
        mini_program_triage_detail=mini_program_triage_detail,
        selected_format=format_name,
        fixture_file_name=fixture_file_name,
        output_dir=output_dir,
    )
    (output_dir / _OUTPUT_FILE_NAMES["demo_summary"]).write_text(
        demo_summary_markdown,
        encoding="utf-8",
    )

    return DemoRunResult(
        output_dir=output_dir,
        import_preview=import_preview,
        import_commit=import_commit,
        paper_progress_summary=paper_progress_summary,
        research_pulse=research_pulse,
        official_account_daily_summary=official_account_daily_summary,
        desktop_notification=desktop_notification,
        mini_program_daily_pulse_detail=mini_program_daily_pulse_detail,
        mini_program_paper_detail=mini_program_paper_detail,
        mini_program_next_actions_detail=mini_program_next_actions_detail,
        mini_program_metadata_attention_detail=mini_program_metadata_attention_detail,
        mini_program_triage_detail=mini_program_triage_detail,
        demo_summary_markdown=demo_summary_markdown,
        selected_format=format_name,
        fixture_file=fixture_file_name,
        pulse_date=resolved_date.isoformat(),
    )


def build_console_summary(result: DemoRunResult) -> str:
    """Return a concise Chinese console summary for local demo runs."""

    return "\n".join(
        [
            (
                "已生成导入预览："
                f"{result.import_preview['valid_records_count']} 条可导入，"
                f"{result.import_preview['warning_records_count']} 条 warning，"
                f"{result.import_preview['error_records_count']} 条不可导入"
            ),
            (f"已生成 Research Pulse 草稿：{result.research_pulse['title']}"),
            "已生成公众号摘要草稿，状态：draft / not_sent（基于 dry_run，本地未发送）",
            (
                "已生成桌面通知草稿，状态："
                f"{result.desktop_notification['delivery_state']} / not_sent"
            ),
            (
                "已生成小程序详情预览，状态："
                f"{result.mini_program_daily_pulse_detail['delivery_state']} / share_safe"
            ),
            f"输出目录：{result.output_dir}",
        ]
    )


@contextmanager
def _isolated_demo_environment() -> Iterator[None]:
    original_env = {key: os.environ.get(key) for key in _ENV_KEYS}
    with tempfile.TemporaryDirectory(prefix="research_pulse_cn_demo_db_") as temp_dir:
        db_path = Path(temp_dir) / "demo.sqlite3"
        os.environ["APP_ENV"] = "test"
        os.environ["APP_LOG_LEVEL"] = "WARNING"
        os.environ["APP_DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
        os.environ["APP_MAX_DELIVERY_RETRIES"] = "2"
        os.environ["APP_DELIVERY_RETRY_DELAY_SECONDS"] = "0"
        os.environ["APP_AUTH_JWT_SECRET"] = "demo-jwt-secret"
        os.environ["APP_AUTH_JWT_ISSUER"] = "demo-issuer"
        os.environ["APP_AUTH_JWT_AUDIENCE"] = "demo-audience"
        os.environ["APP_INTERNAL_SERVICE_TOKEN"] = "demo-internal-service-token"

        get_settings.cache_clear()
        get_metrics().reset()
        reset_official_account_runtime_state()
        reset_db_session_state()
        Base.metadata.create_all(bind=get_engine())
        try:
            yield
        finally:
            Base.metadata.drop_all(bind=get_engine())
            reset_db_session_state()
            get_metrics().reset()
            reset_official_account_runtime_state()
            get_settings.cache_clear()
            for key, previous in original_env.items():
                if previous is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous


def _prepare_admin_access(client: TestClient) -> tuple[dict[str, str], dict[str, str]]:
    session = get_session_factory()()
    try:
        _create_admin_account(
            session,
            email="demo-operator@example.com",
            password="DemoOperator123!",
            role=AdminRole.OPERATOR,
            display_name="Demo Operator",
        )
        _create_admin_account(
            session,
            email="demo-viewer@example.com",
            password="DemoViewer123!",
            role=AdminRole.VIEWER,
            display_name="Demo Viewer",
        )
    finally:
        session.close()

    operator_headers = _login(
        client, email="demo-operator@example.com", password="DemoOperator123!"
    )
    viewer_headers = _login(client, email="demo-viewer@example.com", password="DemoViewer123!")
    return operator_headers, viewer_headers


def _create_admin_account(
    session,
    *,
    email: str,
    password: str,
    role: AdminRole,
    display_name: str,
) -> None:
    account = AdminAccount(
        email=email,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
        is_active=True,
        must_change_password=False,
    )
    session.add(account)
    session.commit()


def _login(client: TestClient, *, email: str, password: str) -> dict[str, str]:
    payload = _request_json(
        client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
    )
    return {"Authorization": f"Bearer {payload['access_token']}"}


def _create_demo_user(client: TestClient, operator_headers: dict[str, str]) -> dict[str, Any]:
    return _request_json(
        client.post(
            "/users",
            headers=operator_headers,
            json=_DEMO_USER_PAYLOAD,
        )
    )


def _create_demo_binding(
    client: TestClient,
    operator_headers: dict[str, str],
    *,
    user_id: str,
) -> dict[str, Any]:
    return _request_json(
        client.post(
            "/admin/wechat-bindings",
            headers=operator_headers,
            json={
                "user_id": user_id,
                "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
                "app_id": "wx-research-pulse-demo",
                "openid": "demo-openid-local-only",
                "bind_state": WeChatBindingState.ACTIVE.value,
                "subscribed": True,
                "digest_enabled": True,
                "display_label": "本地演示公众号",
            },
        )
    )


def _load_fixture_payload(fixture_path: Path, *, format_name: str) -> Any:
    text = fixture_path.read_text(encoding="utf-8")
    if format_name == "pdf_manifest":
        return json.loads(text)
    return text


def _apply_demo_progress_updates(
    client: TestClient,
    operator_headers: dict[str, str],
    *,
    committed_by_source_index: dict[int, str],
) -> None:
    for source_index, payload in _PROGRESS_UPDATES_BY_SOURCE_INDEX.items():
        paper_id = committed_by_source_index.get(source_index)
        if paper_id is None:
            continue
        _request_json(
            client.patch(
                f"/papers/{paper_id}/progress",
                headers=operator_headers,
                json=payload,
            )
        )


def _build_demo_summary_markdown(
    *,
    import_preview: dict[str, Any],
    import_commit: dict[str, Any],
    paper_progress_summary: dict[str, Any],
    research_pulse: dict[str, Any],
    official_account_daily_summary: dict[str, Any],
    desktop_notification: dict[str, Any],
    mini_program_daily_pulse_detail: dict[str, Any],
    mini_program_next_actions_detail: dict[str, Any],
    mini_program_metadata_attention_detail: dict[str, Any],
    mini_program_triage_detail: dict[str, Any],
    selected_format: str,
    fixture_file_name: str,
    output_dir: Path,
) -> str:
    today_focus_titles = _section_item_titles(research_pulse, "today_focus")
    next_action_titles = _section_item_titles(research_pulse, "next_actions")
    metadata_titles = _card_item_titles(mini_program_metadata_attention_detail)
    triage_titles = _card_item_titles(mini_program_triage_detail)
    lines = [
        "# Research Pulse CN MVP 本地演示摘要",
        "",
        (
            "这份输出基于 synthetic demo data，本地离线生成，"
            "不连接真实微信公众号、小程序、桌面通知或外部模型。"
        ),
        "",
        "## 运行信息",
        "",
        f"- 导入格式：`{selected_format}`",
        f"- fixture 文件：`{fixture_file_name}`",
        f"- 输出目录：`{output_dir}`",
        "",
        "## 导入结果",
        "",
        f"- 总记录数：{import_preview['total_records']}",
        f"- 可导入：{import_preview['valid_records_count']}",
        f"- warning 记录：{import_preview['warning_records_count']}",
        f"- 不可导入：{import_preview['error_records_count']}",
        f"- 实际提交：{import_commit['committed_count']}",
        f"- 跳过：{import_commit['skipped_count']}",
        f"- 失败：{import_commit['failed_count']}",
        "",
        "## 论文进度概览",
        "",
        f"- 总论文数：{paper_progress_summary['total_papers']}",
        f"- 阅读中：{paper_progress_summary['reading_count']}",
        f"- 已读：{paper_progress_summary['read_count']}",
        f"- 高优先级：{paper_progress_summary['high_priority_count']}",
        f"- 紧急：{paper_progress_summary['urgent_count']}",
        f"- 已写下一步动作：{paper_progress_summary['with_next_action_count']}",
        "",
        "## 今日 Research Pulse",
        "",
        f"- 标题：{research_pulse['title']}",
        f"- 摘要：{research_pulse['summary']}",
        f"- 今日重点论文：{_join_or_none(today_focus_titles)}",
        f"- 下一步动作论文：{_join_or_none(next_action_titles)}",
        "",
        "## 渠道草稿状态",
        "",
        "- 公众号摘要：draft / not_sent（保持 dry_run，本地未发送）",
        f"- 公众号标题：{official_account_daily_summary['title']}",
        "- 桌面通知：draft / not_sent",
        f"- 桌面通知标题：{desktop_notification['title']}",
        f"- 桌面通知 urgency：{desktop_notification['urgency']}",
        "- 小程序详情：preview / share-safe",
        (f"- 小程序当前 path：{mini_program_daily_pulse_detail['navigation']['current_path']}"),
        "",
        "## 重点待处理内容",
        "",
        f"- 元数据待补全：{_join_or_none(metadata_titles)}",
        f"- 新导入待筛选：{_join_or_none(triage_titles)}",
        f"- 下一步动作详情：{_join_or_none(_card_item_titles(mini_program_next_actions_detail))}",
        "",
        "## 输出文件",
        "",
        "- `import_preview.json`",
        "- `import_commit.json`",
        "- `paper_progress_summary.json`",
        "- `research_pulse.json`",
        "- `official_account_daily_summary.json`",
        "- `desktop_notification.json`",
        "- `mini_program_daily_pulse_detail.json`",
        "- `mini_program_paper_detail.json`",
        "- `mini_program_next_actions_detail.json`",
        "- `mini_program_metadata_attention_detail.json`",
        "- `mini_program_triage_detail.json`",
        "- `demo_summary.md`",
        "",
        "## 边界说明",
        "",
        "- 公众号、桌面和小程序输出都只是草稿或预览。",
        "- 本地演示不会创建真实发送任务，也不会调用系统通知。",
        "- share-safe 规则已经在小程序详情输出里生效。",
    ]
    return "\n".join(lines).strip() + "\n"


def _section_item_titles(payload: dict[str, Any], section_id: str) -> list[str]:
    for section in payload["sections"]:
        if section["section_id"] == section_id:
            return [item["title"] for item in section["items"]]
    return []


def _card_item_titles(payload: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for card in payload["cards"]:
        for item in card["items"]:
            titles.append(item["title"])
    return titles


def _join_or_none(values: list[str]) -> str:
    return "、".join(values) if values else "无"


def _request_json(response) -> dict[str, Any]:
    if response.status_code >= 400:
        raise RuntimeError(
            f"demo request failed: {response.request.method} {response.request.url} -> "
            f"{response.status_code} {response.text}"
        )
    return response.json()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
