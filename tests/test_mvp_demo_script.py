import json
import subprocess
import sys
from pathlib import Path


def test_mvp_demo_script_runs_offline_and_generates_expected_outputs(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "demo-output"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_mvp_demo.py"),
            "--output-dir",
            str(output_dir),
            "--date",
            "2026-04-19",
            "--format",
            "csv",
            "--max-items-per-section",
            "3",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "已生成导入预览" in result.stdout
    assert "已生成 Research Pulse 草稿" in result.stdout
    assert "已生成公众号摘要草稿，状态：draft / not_sent" in result.stdout
    assert "已生成桌面通知草稿，状态：draft / not_sent" in result.stdout
    assert "已生成小程序详情预览，状态：preview / share_safe" in result.stdout

    expected_files = {
        "import_preview.json",
        "import_commit.json",
        "paper_progress_summary.json",
        "research_pulse.json",
        "official_account_daily_summary.json",
        "desktop_notification.json",
        "mini_program_daily_pulse_detail.json",
        "mini_program_paper_detail.json",
        "mini_program_next_actions_detail.json",
        "mini_program_metadata_attention_detail.json",
        "mini_program_triage_detail.json",
        "demo_summary.md",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir()})

    official_payload = json.loads((output_dir / "official_account_daily_summary.json").read_text())
    desktop_payload = json.loads((output_dir / "desktop_notification.json").read_text())
    mini_daily_payload = json.loads(
        (output_dir / "mini_program_daily_pulse_detail.json").read_text()
    )
    mini_metadata_payload = json.loads(
        (output_dir / "mini_program_metadata_attention_detail.json").read_text()
    )
    demo_summary = (output_dir / "demo_summary.md").read_text(encoding="utf-8")

    assert official_payload["dry_run"] is True
    assert official_payload["title"].endswith("公众号每日摘要草稿")
    assert any("草稿" in note for note in official_payload["source_context_notes"])
    assert desktop_payload["delivery_state"] == "draft"
    assert desktop_payload["payload_preview"]["delivery_state"] == "draft"
    assert mini_daily_payload["delivery_state"] == "preview"
    assert mini_daily_payload["share_card"]["share_safe"] is True
    assert "raw_source_payload" not in json.dumps(mini_metadata_payload, ensure_ascii=False)
    assert "user_note" not in json.dumps(mini_metadata_payload, ensure_ascii=False)
    assert "research_note" not in json.dumps(mini_metadata_payload, ensure_ascii=False)

    combined_output = "\n".join(
        [
            result.stdout,
            result.stderr,
            demo_summary,
            (output_dir / "official_account_daily_summary.json").read_text(encoding="utf-8"),
            (output_dir / "desktop_notification.json").read_text(encoding="utf-8"),
            (output_dir / "mini_program_daily_pulse_detail.json").read_text(encoding="utf-8"),
        ]
    )
    forbidden_tokens = [
        "已发送成功",
        "已推送成功",
        "api.weixin.qq.com",
        "openai",
        "anthropic",
        "api_key",
    ]
    for token in forbidden_tokens:
        assert token not in combined_output
