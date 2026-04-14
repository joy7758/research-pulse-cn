from datetime import UTC, datetime, timedelta

from research_pulse_cn.db.models import PaperProfile
from research_pulse_cn.domain.enums import (
    ChannelType,
    DeliveryJobStatus,
    PaperType,
    PulseCardType,
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


def create_user(session, *, email: str = "pulse@example.com"):
    return UserService(session).create_user(
        UserProfileCreate(
            name="Pulse User",
            email=email,
            field="Materials",
            interests=["signals"],
            watched_topics=["citations"],
            watched_venues=["JOM"],
            reminder_preferences={"timezone": "UTC"},
            risk_thresholds={"stalled_days": 14},
        )
    )


def create_paper(
    session,
    *,
    user_id,
    title: str,
    paper_type: PaperType = PaperType.PUBLISHED,
    last_touch_at: datetime | None = None,
    next_action: str | None = None,
    identifiers: dict | None = None,
    venue: str = "JOM",
    priority: int = 4,
) -> PaperProfile:
    return PaperService(session).create_paper(
        PaperProfileCreate(
            user_id=user_id,
            title=title,
            type=paper_type,
            stage=paper_type.value,
            venue=venue,
            identifiers=identifiers or {},
            source_links=[f"https://example.local/papers/{title.replace(' ', '-').lower()}"],
            last_touch_at=last_touch_at,
            next_action=next_action,
            priority=priority,
        )
    )


def add_signal_pair(session, *, paper_id, older: datetime, newer: datetime) -> None:
    paper_service = PaperService(session)
    paper_service.add_signal_snapshot(
        paper_id,
        SignalSnapshotCreate(
            source=SignalSource.GOOGLE_SCHOLAR,
            citation_count=10,
            download_count=50,
            read_count=80,
            inclusion_status="indexed",
            fetched_at=older,
        ),
    )
    paper_service.add_signal_snapshot(
        paper_id,
        SignalSnapshotCreate(
            source=SignalSource.GOOGLE_SCHOLAR,
            citation_count=12,
            download_count=64,
            read_count=105,
            inclusion_status="indexed",
            fetched_at=newer,
        ),
    )


def create_policy(
    session,
    *,
    user_id,
    channel: ChannelType = ChannelType.IN_APP,
    endpoint: str = "console://local",
    frequency_cap: int = 3,
    quiet_hours: dict | None = None,
    policy: dict | None = None,
):
    return SubscriptionPolicyService(session).create_policy(
        SubscriptionPolicyCreate(
            user_id=user_id,
            channel=channel,
            enabled=True,
            frequency=SubscriptionFrequency.EVENT,
            quiet_hours=quiet_hours,
            frequency_cap=frequency_cap,
            endpoint=endpoint,
            policy=policy or {},
        )
    )


def build_service(session, *, now: datetime) -> PulseService:
    return PulseService(session, now_provider=lambda: now)


def test_signal_change_outranks_stalled_progress_when_weight_is_higher(session) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    user = create_user(session)
    create_paper(
        session,
        user_id=user.id,
        title="Stalled paper",
        paper_type=PaperType.UNDER_REVIEW,
        last_touch_at=now - timedelta(days=20),
        next_action=None,
    )
    signal_paper = create_paper(
        session,
        user_id=user.id,
        title="Signal paper",
        last_touch_at=now - timedelta(days=2),
        next_action="Review the latest citations",
    )
    add_signal_pair(
        session,
        paper_id=signal_paper.id,
        older=now - timedelta(days=2),
        newer=now - timedelta(hours=2),
    )
    create_policy(
        session,
        user_id=user.id,
        frequency_cap=1,
        policy={
            "pulse": {
                "score_weights": {
                    "signal_change": 30,
                    "stalled_progress": 10,
                }
            }
        },
    )

    pipeline = build_service(session, now=now).preview(user.id)

    assert pipeline.selected_candidates[0].card_type == PulseCardType.SIGNAL_CHANGE


def test_quiet_hours_suppress_candidates(session) -> None:
    now = datetime(2026, 4, 14, 22, 30, tzinfo=UTC)
    user = create_user(session, email="quiet@example.com")
    paper = create_paper(
        session,
        user_id=user.id,
        title="Quiet hour paper",
        last_touch_at=now - timedelta(days=15),
        next_action="Review the next submission step",
    )
    add_signal_pair(
        session,
        paper_id=paper.id,
        older=now - timedelta(days=1),
        newer=now - timedelta(hours=1),
    )
    create_policy(
        session,
        user_id=user.id,
        quiet_hours={"start": "22:00", "end": "23:00", "timezone": "UTC"},
    )

    pipeline = build_service(session, now=now).preview(user.id)

    assert pipeline.selected_candidates == []
    assert pipeline.suppressed_candidates
    assert any(
        reason.code.value == "quiet_hours"
        for candidate in pipeline.suppressed_candidates
        for reason in candidate.suppression_reasons
    )


def test_frequency_cap_selects_top_n_candidates(session) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    user = create_user(session, email="cap@example.com")
    signal_paper = create_paper(
        session,
        user_id=user.id,
        title="Signal leader",
        last_touch_at=now - timedelta(days=1),
        next_action="Check signal delta",
    )
    create_paper(
        session,
        user_id=user.id,
        title="Stalled runner",
        paper_type=PaperType.UNDER_REVIEW,
        last_touch_at=now - timedelta(days=14),
    )
    create_paper(
        session,
        user_id=user.id,
        title="Action fallback",
        last_touch_at=now - timedelta(days=2),
        next_action="Send follow-up",
    )
    add_signal_pair(
        session,
        paper_id=signal_paper.id,
        older=now - timedelta(days=1),
        newer=now - timedelta(hours=3),
    )
    create_policy(session, user_id=user.id, frequency_cap=2)

    pipeline = build_service(session, now=now).preview(user.id)

    assert len(pipeline.selected_candidates) == 2
    assert any(
        reason.code.value == "frequency_cap"
        for candidate in pipeline.suppressed_candidates
        for reason in candidate.suppression_reasons
    )


def test_dedupe_blocks_repeated_card_selection_within_window(session) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    user = create_user(session, email="dedupe@example.com")
    signal_paper = create_paper(
        session,
        user_id=user.id,
        title="Deduped signal paper",
        last_touch_at=now - timedelta(days=1),
        next_action="Review again",
    )
    add_signal_pair(
        session,
        paper_id=signal_paper.id,
        older=now - timedelta(days=1),
        newer=now - timedelta(hours=1),
    )
    create_policy(session, user_id=user.id)

    first_service = build_service(session, now=now)
    job = first_service.run_now(user.id)
    assert any(card.card_type == PulseCardType.SIGNAL_CHANGE for card in job.cards)

    second_service = build_service(session, now=now + timedelta(hours=1))
    pipeline = second_service.preview(user.id)

    assert any(
        reason.code.value == "dedupe_window"
        for candidate in pipeline.suppressed_candidates
        if candidate.card_type == PulseCardType.SIGNAL_CHANGE
        for reason in candidate.suppression_reasons
    )


def test_paused_papers_produce_no_candidates(session) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    user = create_user(session, email="paused@example.com")
    paused_paper = create_paper(
        session,
        user_id=user.id,
        title="Paused paper",
        paper_type=PaperType.PAUSED,
        last_touch_at=now - timedelta(days=30),
        next_action="Should never produce a pulse",
        identifiers={"deadline_at": (now + timedelta(days=2)).isoformat()},
    )
    add_signal_pair(
        session,
        paper_id=paused_paper.id,
        older=now - timedelta(days=2),
        newer=now - timedelta(hours=2),
    )
    create_policy(session, user_id=user.id)

    pipeline = build_service(session, now=now).preview(user.id)

    assert pipeline.fact_summary["total_facts"] == 0
    assert pipeline.candidates == []


def test_deterministic_tie_break_ordering(session) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    user = create_user(session, email="tie@example.com")
    create_paper(
        session,
        user_id=user.id,
        title="Beta Paper",
        last_touch_at=now - timedelta(days=1),
        next_action="Send beta update",
    )
    create_paper(
        session,
        user_id=user.id,
        title="Alpha Paper",
        last_touch_at=now - timedelta(days=1),
        next_action="Send alpha update",
    )
    create_policy(session, user_id=user.id, frequency_cap=2)

    pipeline = build_service(session, now=now).preview(user.id)

    selected_titles = [candidate.paper_title for candidate in pipeline.selected_candidates]
    assert selected_titles[:2] == ["Alpha Paper", "Beta Paper"]
    assert pipeline.ordering_explanation["sort_fields"][0] == "score_total desc"


def test_delivery_retry_then_dead_letter(session) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    user = create_user(session, email="delivery@example.com")
    signal_paper = create_paper(
        session,
        user_id=user.id,
        title="Delivery paper",
        last_touch_at=now - timedelta(days=2),
        next_action="Review signal before send",
    )
    add_signal_pair(
        session,
        paper_id=signal_paper.id,
        older=now - timedelta(days=1),
        newer=now - timedelta(hours=2),
    )
    create_policy(
        session,
        user_id=user.id,
        channel=ChannelType.DINGTALK,
        endpoint="https://fail.example.local/webhook",
    )

    pulse_service = build_service(session, now=now)
    delivery_service = DeliveryService(session)

    job = pulse_service.run_now(user.id)
    assert any(delivery.status == DeliveryJobStatus.FAILED for delivery in job.delivery_jobs)

    delivery_service.dispatch_due_jobs()
    refreshed_job = pulse_service.get_job(job.id)
    assert any(
        delivery.status == DeliveryJobStatus.DEAD_LETTER for delivery in refreshed_job.delivery_jobs
    )
