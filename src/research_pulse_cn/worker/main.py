"""Simple worker entrypoint for pulse jobs and outbox delivery."""

from __future__ import annotations

import argparse
import time

from research_pulse_cn.db.session import get_session_factory
from research_pulse_cn.services.pulse import PulseService


def run_worker(*, once: bool, limit: int, poll_interval: int) -> None:
    session_factory = get_session_factory()
    while True:
        session = session_factory()
        try:
            PulseService(session).process_pending_jobs(limit=limit)
        finally:
            session.close()
        if once:
            return
        time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending pulse and delivery jobs.")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle and exit.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum pending jobs per cycle.")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=15,
        help="Seconds between polling cycles in daemon mode.",
    )
    args = parser.parse_args()
    run_worker(once=args.once, limit=args.limit, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
