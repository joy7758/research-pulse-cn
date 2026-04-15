from datetime import UTC, datetime, timedelta

from research_pulse_cn.db.models import PaperProfile
from research_pulse_cn.domain.enums import (
    ChannelType,
    DeliveryJobStatus,
    PaperType,
    PulseCardType,
    SignalSource,
    SubscriptionFrequency,
    WorkActivitySource,
    WorkActivityType,
)
from research_pulse_cn.schemas.paper import PaperProfileCreate, SignalSnapshotCreate
from research_pulse_cn.schemas.subscription_policy import SubscriptionPolicyCreate
from research_pulse_cn.schemas.user import UserProfileCreate
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.digest import DigestService
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.pulse import PulseService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService
from research_pulse_cn.services.user import UserService
from research_pulse_cn.services.work_activity import WorkActivityService


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
    blocker: str | None = None,
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
            blocker=blocker,
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
    frequency: SubscriptionFrequency = SubscriptionFrequency.EVENT,
    quiet_hours: dict | None = None,
    policy: dict | None = None,
):
    return SubscriptionPolicyService(session).create_policy(
        SubscriptionPolicyCreate(
            user_id=user_id,
            channel=channel,
            enabled=True,
            frequency=frequency,
            quiet_hours=quiet_hours,
            frequency_cap=frequency_cap,
            endpoint=endpoint,
            policy=policy or {},
        )
    )


def build_service(session, *, now: datetime) -> PulseService:
    return PulseService(session, now_provider=lambda: now)


def record_work_activity(
    session,
    *,
    user_id,
    paper_id=None,
    activity_type: WorkActivityType,
    summary: str,
    happened_at: datetime,
    source: WorkActivitySource = WorkActivitySource.API,
):
    return WorkActivityService(session).record_event(
        user_id=user_id,
        paper_id=paper_id,
        activity_type=activity_type,
        summary=summary,
        happened_at=happened_at,
        source=source,
    )


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
        channel=ChannelType.WEBHOOK,
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


def test_no_yesterday_summary_candidate_when_previous_local_day_has_zero_events(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="no-yesterday-summary@example.com")

    pipeline = build_service(session, now=now).preview(user.id)

    assert all(fact.card_type != PulseCardType.YESTERDAY_SUMMARY for fact in pipeline.facts)
    assert all(
        candidate.card_type != PulseCardType.YESTERDAY_SUMMARY for candidate in pipeline.candidates
    )


def test_no_today_suggestion_candidate_when_no_actionable_papers(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="no-today-suggestion@example.com")
    create_paper(
        session,
        user_id=user.id,
        title="Paused paper",
        paper_type=PaperType.PAUSED,
        last_touch_at=now - timedelta(days=20),
        next_action="Do not surface this",
    )

    pipeline = build_service(session, now=now).preview(user.id)

    assert all(fact.card_type != PulseCardType.TODAY_SUGGESTION for fact in pipeline.facts)
    assert all(
        candidate.card_type != PulseCardType.TODAY_SUGGESTION for candidate in pipeline.candidates
    )


def test_today_suggestion_candidate_appears_for_explicit_next_action(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-next-action@example.com")
    paper = create_paper(
        session,
        user_id=user.id,
        title="Today action paper",
        paper_type=PaperType.REVISION,
        last_touch_at=now - timedelta(days=6),
        next_action="Draft the revision cover letter.",
        priority=5,
    )

    pipeline = build_service(session, now=now).preview(user.id)
    candidate = next(
        candidate
        for candidate in pipeline.candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    )

    assert candidate.source_paper_id == paper.id
    assert candidate.candidate_metadata["suggestion_kind"] == "execute_next_action"
    assert candidate.candidate_metadata["paper_title"] == paper.title
    assert candidate.score_total >= 10


def test_today_suggestion_candidate_can_resolve_blocker(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-blocker@example.com")
    create_paper(
        session,
        user_id=user.id,
        title="Blocked revision paper",
        paper_type=PaperType.REVISION,
        last_touch_at=now - timedelta(days=4),
        blocker="Need co-author approval on Figure 3.",
        next_action="Submit the revision response package.",
        priority=4,
    )

    pipeline = build_service(session, now=now).preview(user.id)
    candidate = next(
        candidate
        for candidate in pipeline.candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    )

    assert candidate.candidate_metadata["suggestion_kind"] == "resolve_blocker"
    assert candidate.candidate_metadata["blocker"] == "Need co-author approval on Figure 3."


def test_today_suggestion_candidate_can_define_next_action(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-define-action@example.com")
    create_paper(
        session,
        user_id=user.id,
        title="Actionless prep paper",
        paper_type=PaperType.IN_PREP,
        last_touch_at=now - timedelta(days=8),
        next_action=None,
        priority=4,
    )

    pipeline = build_service(session, now=now).preview(user.id)
    candidate = next(
        candidate
        for candidate in pipeline.candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    )

    assert candidate.candidate_metadata["suggestion_kind"] == "define_next_action"
    assert candidate.candidate_metadata["next_action"] is None


def test_paused_papers_are_excluded_from_today_suggestion(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-paused-excluded@example.com")
    create_paper(
        session,
        user_id=user.id,
        title="Paused but tempting",
        paper_type=PaperType.PAUSED,
        last_touch_at=now - timedelta(days=12),
        next_action="Should not appear",
        priority=5,
    )
    create_paper(
        session,
        user_id=user.id,
        title="Active paper",
        paper_type=PaperType.UNDER_REVIEW,
        last_touch_at=now - timedelta(days=3),
        next_action="Respond to the open reviewer question.",
        priority=3,
    )

    pipeline = build_service(session, now=now).preview(user.id)
    candidate = next(
        candidate
        for candidate in pipeline.candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    )

    assert candidate.candidate_metadata["paper_title"] == "Active paper"


def test_today_suggestion_scoring_is_deterministic_and_explainable(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-score@example.com")
    create_paper(
        session,
        user_id=user.id,
        title="Deterministic revision",
        paper_type=PaperType.REVISION,
        last_touch_at=now - timedelta(days=7),
        next_action="Update the reviewer response table.",
        priority=5,
    )

    first = build_service(session, now=now).preview(user.id)
    second = build_service(session, now=now).preview(user.id)
    first_candidate = next(
        candidate
        for candidate in first.candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    )
    second_candidate = next(
        candidate
        for candidate in second.candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    )

    assert first_candidate.score_total == second_candidate.score_total
    assert first_candidate.score_breakdown is not None
    assert first_candidate.score_breakdown.modifiers == {
        "today_suggestion_priority": 5,
        "today_suggestion_has_next_action": 3,
        "today_suggestion_revision_stage": 3,
        "today_suggestion_stale_progress": 3,
    }


def test_today_suggestion_dedupe_blocks_same_context(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-dedupe@example.com")
    paper = create_paper(
        session,
        user_id=user.id,
        title="Dedupe paper",
        paper_type=PaperType.UNDER_REVIEW,
        last_touch_at=now - timedelta(days=6),
        next_action="Send the clarified methods paragraph.",
        priority=4,
    )

    first_service = build_service(session, now=now)
    job = first_service.run_now(user.id)
    assert any(card.card_type == PulseCardType.TODAY_SUGGESTION for card in job.cards)

    pipeline = build_service(session, now=now + timedelta(hours=1)).preview(user.id)
    suppressed = [
        candidate
        for candidate in pipeline.suppressed_candidates
        if candidate.card_type == PulseCardType.TODAY_SUGGESTION
    ]

    assert suppressed
    assert suppressed[0].source_paper_id == paper.id
    assert any(reason.code.value == "dedupe_window" for reason in suppressed[0].suppression_reasons)


def test_yesterday_summary_candidate_appears_for_previous_day_activity(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="with-yesterday-summary@example.com")
    paper = create_paper(
        session,
        user_id=user.id,
        title="Yesterday Summary Paper",
        last_touch_at=now,
        next_action=None,
        priority=3,
    )
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=paper.id,
        activity_type=WorkActivityType.NOTE_SAVED,
        summary="Saved a local revision note.",
        happened_at=now - timedelta(days=1, hours=2),
    )

    pipeline = build_service(session, now=now).preview(user.id)
    candidate = next(
        candidate
        for candidate in pipeline.candidates
        if candidate.card_type == PulseCardType.YESTERDAY_SUMMARY
    )

    assert candidate.score_total >= 10
    assert candidate.score_breakdown is not None
    assert candidate.candidate_metadata["summary_date"] == "2026-04-14"
    assert candidate.candidate_metadata["total_events"] == 1
    assert candidate.candidate_metadata["touched_paper_titles"] == [paper.title]


def test_system_work_activity_is_excluded_from_yesterday_summary(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="system-excluded@example.com")
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=None,
        activity_type=WorkActivityType.NOTE_CREATED,
        summary="System generated placeholder event.",
        happened_at=now - timedelta(days=1, hours=3),
        source=WorkActivitySource.SYSTEM,
    )

    pipeline = build_service(session, now=now).preview(user.id)

    assert all(
        candidate.card_type != PulseCardType.YESTERDAY_SUMMARY for candidate in pipeline.candidates
    )


def test_yesterday_summary_scoring_is_deterministic_and_explainable(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="yesterday-score@example.com")
    paper_a = create_paper(
        session,
        user_id=user.id,
        title="Paper A",
        last_touch_at=now,
        next_action=None,
    )
    paper_b = create_paper(
        session,
        user_id=user.id,
        title="Paper B",
        last_touch_at=now,
        next_action=None,
    )
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=paper_a.id,
        activity_type=WorkActivityType.NOTE_SAVED,
        summary="Saved a planning note.",
        happened_at=now - timedelta(days=1, hours=4),
    )
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=paper_b.id,
        activity_type=WorkActivityType.ATTACHMENT_IMPORTED,
        summary="Imported revised figures.",
        happened_at=now - timedelta(days=1, hours=3),
    )
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=paper_a.id,
        activity_type=WorkActivityType.REVIEW_ROUND_CREATED,
        summary="Created review round 1.",
        happened_at=now - timedelta(days=1, hours=2),
    )

    first = build_service(session, now=now).preview(user.id)
    second = build_service(session, now=now).preview(user.id)
    first_candidate = next(
        candidate
        for candidate in first.candidates
        if candidate.card_type == PulseCardType.YESTERDAY_SUMMARY
    )
    second_candidate = next(
        candidate
        for candidate in second.candidates
        if candidate.card_type == PulseCardType.YESTERDAY_SUMMARY
    )

    assert first_candidate.score_total == second_candidate.score_total
    assert first_candidate.score_breakdown is not None
    assert first_candidate.score_breakdown.modifiers == {
        "yesterday_summary_activity_diversity": 3,
        "yesterday_summary_event_volume": 2,
        "yesterday_summary_multi_paper": 4,
    }


def test_yesterday_summary_uses_daily_policy_timezone(session) -> None:
    now = datetime(2026, 4, 15, 4, 0, tzinfo=UTC)
    user = create_user(session, email="yesterday-timezone@example.com")
    create_policy(
        session,
        user_id=user.id,
        frequency=SubscriptionFrequency.DAILY,
        policy={"schedule": {"timezone": "Asia/Shanghai"}},
    )
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=None,
        activity_type=WorkActivityType.NOTE_CREATED,
        summary="Created a note after local midnight.",
        happened_at=datetime(2026, 4, 14, 18, 0, tzinfo=UTC),
    )

    pipeline = build_service(session, now=now).preview(user.id)

    assert all(
        candidate.card_type != PulseCardType.YESTERDAY_SUMMARY for candidate in pipeline.candidates
    )


def test_yesterday_summary_dedupe_blocks_same_summary_date(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="yesterday-dedupe@example.com")
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=None,
        activity_type=WorkActivityType.NOTE_SAVED,
        summary="Saved an outline note.",
        happened_at=now - timedelta(days=1, hours=2),
    )

    first_service = build_service(session, now=now)
    job = first_service.run_now(user.id)
    assert any(card.card_type == PulseCardType.YESTERDAY_SUMMARY for card in job.cards)

    pipeline = build_service(session, now=now + timedelta(hours=1)).preview(user.id)
    suppressed = [
        candidate
        for candidate in pipeline.suppressed_candidates
        if candidate.card_type == PulseCardType.YESTERDAY_SUMMARY
    ]

    assert suppressed
    assert any(reason.code.value == "dedupe_window" for reason in suppressed[0].suppression_reasons)


def test_run_persists_yesterday_summary_card_and_digest_item(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="yesterday-run@example.com")
    record_work_activity(
        session,
        user_id=user.id,
        paper_id=None,
        activity_type=WorkActivityType.NOTE_SAVED,
        summary="Saved a revision note.",
        happened_at=now - timedelta(days=1, hours=2),
    )

    job = build_service(session, now=now).run_now(user.id)
    yesterday_card = next(
        card for card in job.cards if card.card_type == PulseCardType.YESTERDAY_SUMMARY
    )
    digest_issue = DigestService(session).list_digest_issues(user_id=user.id)[0]

    assert yesterday_card.source_paper_id is None
    assert yesterday_card.candidate_metadata["summary_date"] == "2026-04-14"
    assert digest_issue.items[0].card_type == PulseCardType.YESTERDAY_SUMMARY
    assert digest_issue.items[0].source_paper_id is None


def test_run_persists_today_suggestion_card_and_digest_item(session) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    user = create_user(session, email="today-run@example.com")
    paper = create_paper(
        session,
        user_id=user.id,
        title="Today run paper",
        paper_type=PaperType.REVISION,
        last_touch_at=now - timedelta(days=6),
        next_action="Finalize the revision cover note.",
        priority=5,
    )

    job = build_service(session, now=now).run_now(user.id)
    today_card = next(
        card for card in job.cards if card.card_type == PulseCardType.TODAY_SUGGESTION
    )
    digest_issue = DigestService(session).list_digest_issues(user_id=user.id)[0]

    assert today_card.source_paper_id == paper.id
    assert today_card.candidate_metadata["suggestion_kind"] == "execute_next_action"
    assert any(item.card_type == PulseCardType.TODAY_SUGGESTION for item in digest_issue.items)
