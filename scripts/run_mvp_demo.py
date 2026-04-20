"""Run the local offline MVP demo with synthetic fixture data."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from research_pulse_cn.demo.mvp_local_demo import (  # noqa: E402
    available_fixture_formats,
    build_console_summary,
    run_mvp_demo,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Research Pulse CN MVP local demo with synthetic fixture data."
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=REPO_ROOT / "demo" / "fixtures" / "mvp",
        help="Directory that stores synthetic MVP demo fixtures.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/research_pulse_cn_demo"),
        help="Directory used for generated demo JSON and Markdown artifacts.",
    )
    parser.add_argument(
        "--format",
        choices=available_fixture_formats(),
        default="csv",
        help="Fixture import format used for the local demo.",
    )
    parser.add_argument(
        "--date",
        default="2026-04-19",
        help="Pulse date used in the demo, in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--max-items-per-section",
        type=int,
        default=3,
        help="Maximum items kept in each pulse section or preview list.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_mvp_demo(
        fixture_dir=args.fixture_dir,
        output_dir=args.output_dir,
        format_name=args.format,
        pulse_date=date.fromisoformat(args.date),
        max_items_per_section=args.max_items_per_section,
    )
    print(build_console_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
