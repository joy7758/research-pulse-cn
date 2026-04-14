from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    DeliveryJobStatus,
    PaperType,
    SignalSource,
    SubscriptionFrequency,
)
from research_pulse_cn.schemas.paper import PaperProfileCreate, SignalSnapshotCreate
from research_pulse_cn.schemas.subscription_policy import SubscriptionPolicyCreate
from research_pulse_cn.schemas.user import UserProfileCreate
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.pulse import PulseService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService
from research_pulse_cn.services.user import UserService


def build_pulse_ready_state(session, *, channel: ChannelType, endpoint: str):
    user_service = UserService(session)
    paper_service = PaperService(session)
    policy_service = SubscriptionPolicyService(session)

    user = user_service.create_user(
        UserProfileCreate(
            name="Pulse User",
            email="pulse@example.com",
            field="Materials",
            interests=["signals"],
            watched_topics=["citations"],
            watched_venues=["JOM"],
            reminder_preferences={"timezone": "UTC"},
            risk_thresholds={"stalled_days": 14},
        )
    )
    paper = paper_service.create_paper(
        PaperProfileCreate(
            user_id=user.id,
            title="Signal-heavy paper",
            type=PaperType.PUBLISHED,
            stage="published",
            venue="JOM",
            identifiers={"doi": "10.0000/demo"},
            source_links=["https://example.local/papers/signal-heavy"],
            last_touch_at=utcnow() - timedelta(days=21),
            next_action="Share the latest trend with stakeholders",
            priority=4,
        )
    )
    paper_service.add_signal_snapshot(
        paper.id,
        SignalSnapshotCreate(
            source=SignalSource.GOOGLE_SCHOLAR,
            citation_count=10,
            download_count=50,
            read_count=80,
            inclusion_status="indexed",
            fetched_at=utcnow() - timedelta(days=7),
        ),
    )
    paper_service.add_signal_snapshot(
        paper.id,
        SignalSnapshotCreate(
            source=SignalSource.GOOGLE_SCHOLAR,
            citation_count=12,
            download_count=64,
            read_count=105,
            inclusion_status="indexed",
            fetched_at=utcnow(),
        ),
    )
    policy_service.create_policy(
        SubscriptionPolicyCreate(
            user_id=user.id,
            channel=channel,
            enabled=True,
            frequency=SubscriptionFrequency.EVENT,
            endpoint=endpoint,
            policy={"mode": "test"},
        )
    )
    return user


def test_pulse_preview_and_run_generates_cards_and_delivery_jobs(session) -> None:
    user = build_pulse_ready_state(session, channel=ChannelType.IN_APP, endpoint="console://local")
    pulse_service = PulseService(session)

    preview_cards = pulse_service.preview(user.id)
    assert len(preview_cards) >= 2

    job = pulse_service.run_now(user.id)
    assert job.status.value == "completed"
    assert len(job.cards) >= 2
    assert len(job.delivery_jobs) >= 2
    assert all(delivery.status == DeliveryJobStatus.SENT for delivery in job.delivery_jobs)


def test_delivery_retry_then_dead_letter(session) -> None:
    user = build_pulse_ready_state(
        session,
        channel=ChannelType.DINGTALK,
        endpoint="https://fail.example.local/webhook",
    )
    pulse_service = PulseService(session)
    delivery_service = DeliveryService(session)

    job = pulse_service.run_now(user.id)
    assert any(delivery.status == DeliveryJobStatus.FAILED for delivery in job.delivery_jobs)

    delivery_service.dispatch_due_jobs()
    refreshed_job = pulse_service.get_job(job.id)
    assert any(
        delivery.status == DeliveryJobStatus.DEAD_LETTER for delivery in refreshed_job.delivery_jobs
    )
