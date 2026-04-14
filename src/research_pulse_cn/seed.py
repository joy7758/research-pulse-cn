"""Seed demo data for local development."""

from __future__ import annotations

from datetime import timedelta

from research_pulse_cn.db.models import Base, utcnow
from research_pulse_cn.db.session import get_engine, get_session_factory
from research_pulse_cn.domain.enums import (
    ChannelType,
    PaperType,
    SignalSource,
    SubscriptionFrequency,
)
from research_pulse_cn.schemas.paper import (
    PaperProfileCreate,
    ProgressEventCreate,
    SignalSnapshotCreate,
)
from research_pulse_cn.schemas.subscription_policy import SubscriptionPolicyCreate
from research_pulse_cn.schemas.user import UserProfileCreate
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService
from research_pulse_cn.services.user import UserService


def seed_demo_data() -> None:
    """Create demo data for one user and a representative paper set."""
    Base.metadata.create_all(bind=get_engine())

    session = get_session_factory()()
    try:
        user_service = UserService(session)
        paper_service = PaperService(session)
        policy_service = SubscriptionPolicyService(session)

        if user_service.list_users():
            return

        user = user_service.create_user(
            UserProfileCreate(
                name="Demo Researcher",
                email="demo@research-pulse.local",
                field="Materials Science",
                interests=["alloy optimization", "surface engineering"],
                watched_topics=["fatigue", "heat treatment"],
                watched_venues=["TSE", "JOM"],
                reminder_preferences={"timezone": "Asia/Shanghai"},
                risk_thresholds={"stalled_days": 14},
            )
        )

        paper_a = paper_service.create_paper(
            PaperProfileCreate(
                user_id=user.id,
                title="China fatigue study on advanced steel joints",
                title_zh="先进钢接头疲劳研究",
                type=PaperType.UNDER_REVIEW,
                stage="under_review",
                venue="TSE",
                identifiers={"internal_code": "RP-001"},
                source_links=["https://example.local/papers/rp-001"],
                last_touch_at=utcnow() - timedelta(days=21),
                next_action="Prepare revision memo for reviewer #2",
                blocker="Awaiting co-author figures",
                priority=4,
            )
        )
        paper_b = paper_service.create_paper(
            PaperProfileCreate(
                user_id=user.id,
                title="High-entropy alloy inclusion trend watch",
                title_en="High-entropy alloy inclusion trend watch",
                type=PaperType.PUBLISHED,
                stage="published",
                venue="JOM",
                identifiers={"doi": "10.0000/example"},
                source_links=["https://example.local/papers/rp-002"],
                last_touch_at=utcnow() - timedelta(days=3),
                next_action="Share the latest citation delta with the team",
                priority=3,
            )
        )

        paper_service.add_progress_event(
            paper_a.id,
            ProgressEventCreate(
                stage="under_review",
                happened_at=utcnow() - timedelta(days=21),
                summary="Submitted revised manuscript and waiting for editor feedback.",
                evidence_links=["https://example.local/events/revision-submitted"],
                owner="demo-owner",
            ),
        )
        paper_service.add_signal_snapshot(
            paper_b.id,
            SignalSnapshotCreate(
                source=SignalSource.GOOGLE_SCHOLAR,
                citation_count=12,
                download_count=35,
                read_count=80,
                inclusion_status="indexed",
                fetched_at=utcnow() - timedelta(days=7),
            ),
        )
        paper_service.add_signal_snapshot(
            paper_b.id,
            SignalSnapshotCreate(
                source=SignalSource.GOOGLE_SCHOLAR,
                citation_count=14,
                download_count=43,
                read_count=96,
                inclusion_status="indexed",
                fetched_at=utcnow(),
            ),
        )

        policy_service.create_policy(
            SubscriptionPolicyCreate(
                user_id=user.id,
                channel=ChannelType.IN_APP,
                enabled=True,
                frequency=SubscriptionFrequency.EVENT,
                endpoint="console://local",
                policy={"digest": False},
            )
        )
        policy_service.create_policy(
            SubscriptionPolicyCreate(
                user_id=user.id,
                channel=ChannelType.DINGTALK,
                enabled=True,
                frequency=SubscriptionFrequency.DAILY,
                endpoint="https://oapi.dingtalk.local/webhook/demo",
                policy={"signing": "stub"},
            )
        )
    finally:
        session.close()


if __name__ == "__main__":
    seed_demo_data()
