"""Simple worker entrypoint for pulse jobs and outbox delivery."""

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
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.heartbeat import WorkerHeartbeatService
from research_pulse_cn.services.pulse import PulseService

logger = logging.getLogger(__name__)


def run_worker(*, once: bool, limit: int, poll_interval: int) -> None:
    configure_logging(get_settings())
    session_factory = get_session_factory()
    worker_name = "delivery-worker"
    while True:
        session = session_factory()
        try:
            heartbeat_service = WorkerHeartbeatService(session)
            heartbeat_service.beat(
                worker_name=worker_name,
                worker_role=WorkerRole.DELIVERY_WORKER,
                status=WorkerStatus.RUNNING,
                metadata={"limit": limit, "poll_interval": poll_interval},
                now=utcnow(),
            )
            with bind_log_context(worker_role=WorkerRole.DELIVERY_WORKER.value):
                pulse_jobs = PulseService(session).process_pending_jobs(
                    limit=limit,
                    lease_owner=worker_name,
                )
                delivery_jobs = DeliveryService(session).dispatch_due_jobs(limit=limit)
                heartbeat_service.beat(
                    worker_name=worker_name,
                    worker_role=WorkerRole.DELIVERY_WORKER,
                    status=WorkerStatus.IDLE,
                    metadata={
                        "processed_pulse_jobs": len(pulse_jobs),
                        "processed_delivery_jobs": len(delivery_jobs),
                    },
                    now=utcnow(),
                )
        except Exception as exc:
            session.rollback()
            WorkerHeartbeatService(session).beat(
                worker_name=worker_name,
                worker_role=WorkerRole.DELIVERY_WORKER,
                status=WorkerStatus.ERROR,
                metadata={"error": str(exc)},
                now=utcnow(),
            )
            logger.exception("worker loop failed")
            if once:
                raise
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
