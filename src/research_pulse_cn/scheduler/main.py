"""Scheduler worker entrypoint."""

from __future__ import annotations

import argparse
import logging
import time

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.logging import configure_logging
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.db.session import get_session_factory
from research_pulse_cn.domain.enums import WorkerRole, WorkerStatus
from research_pulse_cn.services.heartbeat import WorkerHeartbeatService
from research_pulse_cn.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)


def run_scheduler(*, once: bool, poll_interval: int) -> None:
    configure_logging(get_settings())
    session_factory = get_session_factory()
    worker_name = "daily-scheduler"
    while True:
        session = session_factory()
        try:
            heartbeat_service = WorkerHeartbeatService(session)
            heartbeat_service.beat(
                worker_name=worker_name,
                worker_role=WorkerRole.SCHEDULER,
                status=WorkerStatus.RUNNING,
                metadata={"poll_interval": poll_interval},
                now=utcnow(),
            )
            with bind_log_context(worker_role=WorkerRole.SCHEDULER.value):
                tick_result = SchedulerService(session).tick()
                heartbeat_service.beat(
                    worker_name=worker_name,
                    worker_role=WorkerRole.SCHEDULER,
                    status=WorkerStatus.IDLE,
                    metadata={
                        "jobs_created": tick_result["jobs_created"],
                        "jobs_existing": tick_result["jobs_existing"],
                        "jobs_skipped_not_due": tick_result["jobs_skipped_not_due"],
                    },
                    now=utcnow(),
                )
        except Exception as exc:
            session.rollback()
            WorkerHeartbeatService(session).beat(
                worker_name=worker_name,
                worker_role=WorkerRole.SCHEDULER,
                status=WorkerStatus.ERROR,
                metadata={"error": str(exc)},
                now=utcnow(),
            )
            logger.exception("scheduler loop failed")
            if once:
                raise
        finally:
            session.close()
        if once:
            return
        time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Schedule due daily pulse jobs.")
    parser.add_argument("--once", action="store_true", help="Run one scheduler tick and exit.")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Seconds between scheduler ticks in daemon mode.",
    )
    args = parser.parse_args()
    run_scheduler(once=args.once, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
