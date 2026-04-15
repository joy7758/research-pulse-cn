from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import research_pulse_cn.services.external_retrieval as external_retrieval_module
from research_pulse_cn.db.models import (
    ExternalRetrievalPlan,
    ExternalRetrievalRun,
    ExternalRetrievedRecord,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ExternalRetrievalPlanStatus,
    ExternalRetrievalRunStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
    PaperType,
    PulseCardType,
    SignalSource,
    SubscriptionFrequency,
    WorkActivitySource,
    WorkActivityType,
)
from research_pulse_cn.services.work_activity import WorkActivityService


def create_api_user(client, *, email: str, headers: dict[str, str]):
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "API Pulse User",
            "email": email,
            "field": "Materials",
            "interests": ["signals"],
            "watched_topics": ["citations"],
            "watched_venues": ["JOM"],
            "reminder_preferences": {"timezone": "UTC"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_api_paper(
    client,
    *,
    user_id: str,
    title: str,
    headers: dict[str, str],
    paper_type: PaperType = PaperType.PUBLISHED,
    stage: str | None = None,
    last_touch_at: str | None = None,
    next_action: str | None = "Check the latest signal delta",
    blocker: str | None = None,
    priority: int = 4,
):
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": paper_type,
            "stage": stage or paper_type.value,
            "venue": "JOM",
            "identifiers": {},
            "source_links": [f"https://example.local/papers/{title.replace(' ', '-').lower()}"],
            "last_touch_at": last_touch_at or (utcnow() - timedelta(days=14)).isoformat(),
            "next_action": next_action,
            "blocker": blocker,
            "priority": priority,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_api_signal_pair(client, *, paper_id: str, headers: dict[str, str]) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (13, 68, 111, newer),
    ):
        response = client.post(
            f"/papers/{paper_id}/signal-snapshots",
            headers=headers,
            json={
                "source": SignalSource.GOOGLE_SCHOLAR,
                "citation_count": citation_count,
                "download_count": download_count,
                "read_count": read_count,
                "inclusion_status": "indexed",
                "fetched_at": fetched_at.isoformat(),
            },
        )
        assert response.status_code == 201


def create_api_policy(
    client,
    *,
    user_id: str,
    headers: dict[str, str],
    quiet_hours: dict | None = None,
):
    response = client.post(
        "/subscription-policies",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": "in_app",
            "enabled": True,
            "frequency": SubscriptionFrequency.EVENT,
            "quiet_hours": quiet_hours,
            "frequency_cap": 2,
            "endpoint": "console://local",
            "policy": {"pulse": {"score_weights": {"signal_change": 22}}},
        },
    )
    assert response.status_code == 201


def create_completed_related_record(
    session,
    *,
    user_id: str,
    paper_id: str,
    title: str,
    doi: str = "10.1234/api-related-paper",
    external_id: str = "https://openalex.org/W999",
    finished_at: datetime | None = None,
) -> ExternalRetrievedRecord:
    finished_at = finished_at or datetime(2026, 4, 15, 8, 0, tzinfo=UTC)
    plan = ExternalRetrievalPlan(
        user_id=UUID(user_id),
        source_kind=ExternalRetrievalSourceKind.OPENALEX,
        retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
        watch_profile_id=None,
        paper_id=UUID(paper_id),
        plan_label="OpenAlex related papers",
        query_text=title,
        query_payload={"keywords": [title]},
        effective_inputs={"keywords": [title]},
        reason_codes=["watch_keywords_present", "recent_touched_paper_context"],
        plan_hash=f"api-related:{uuid4().hex}",
        status=ExternalRetrievalPlanStatus.PLANNED,
    )
    session.add(plan)
    session.flush()

    run = ExternalRetrievalRun(
        plan_id=plan.id,
        user_id=UUID(user_id),
        source_kind=ExternalRetrievalSourceKind.OPENALEX,
        retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
        status=ExternalRetrievalRunStatus.COMPLETED,
        request_url="https://api.openalex.org/works?search=api-related",
        request_payload={"params": {"search": title}},
        response_summary={"raw_result_count": 1},
        raw_result_count=1,
        normalized_result_count=1,
        started_at=finished_at,
        finished_at=finished_at,
        last_error=None,
    )
    session.add(run)
    session.flush()

    record = ExternalRetrievedRecord(
        run_id=run.id,
        plan_id=plan.id,
        user_id=UUID(user_id),
        source_kind=ExternalRetrievalSourceKind.OPENALEX,
        retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
        external_id=external_id,
        external_url="https://example.org/api-related-result",
        doi=doi,
        title=title,
        abstract_snippet="Compact related paper summary.",
        publication_year=2024,
        publication_date="2024-02-01",
        source_title="Acta Materialia",
        authors=[{"name": "Alice Zhang"}, {"name": "Bo Li"}],
        matched_reason_codes=["watch_keywords_present", "recent_touched_paper_context"],
        raw_payload={"title": title},
        sort_order=1,
    )
    session.add(record)
    session.commit()
    return record


def test_preview_endpoint_exposes_suppression_reasons_and_score_breakdowns(
    client,
    viewer_headers,
    operator_headers,
) -> None:
    now = utcnow()
    start = (now - timedelta(minutes=30)).time().replace(microsecond=0).isoformat()
    end = (now + timedelta(minutes=30)).time().replace(microsecond=0).isoformat()

    user = create_api_user(client, email="preview-api@example.com", headers=operator_headers)
    paper = create_api_paper(
        client,
        user_id=user["id"],
        title="Preview API paper",
        headers=operator_headers,
    )
    add_api_signal_pair(client, paper_id=paper["id"], headers=operator_headers)
    create_api_policy(
        client,
        user_id=user["id"],
        headers=operator_headers,
        quiet_hours={"start": start, "end": end, "timezone": "UTC"},
    )

    response = client.post(f"/pulse/preview/{user['id']}", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fact_summary"]["total_facts"] >= 1
    assert payload["candidates"][0]["score_breakdown"]["total"] >= 0
    assert payload["suppressed_candidates"]
    assert any(
        reason["code"] == "quiet_hours"
        for candidate in payload["suppressed_candidates"]
        for reason in candidate["suppression_reasons"]
    )


def test_run_endpoint_persists_selected_cards_with_score_fields(client, operator_headers) -> None:
    user = create_api_user(client, email="run-api@example.com", headers=operator_headers)
    paper = create_api_paper(
        client,
        user_id=user["id"],
        title="Run API paper",
        headers=operator_headers,
    )
    add_api_signal_pair(client, paper_id=paper["id"], headers=operator_headers)
    create_api_policy(client, user_id=user["id"], headers=operator_headers)

    response = client.post(f"/pulse/run/{user['id']}", headers=operator_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["cards"]
    assert payload["cards"][0]["source_paper_id"] == paper["id"]
    assert payload["cards"][0]["score_total"] >= 10
    assert payload["cards"][0]["score_breakdown"]["total"] == payload["cards"][0]["score_total"]


def test_preview_endpoint_exposes_yesterday_summary_details(
    client,
    operator_headers,
    viewer_headers,
    session,
) -> None:
    user = create_api_user(
        client,
        email="yesterday-preview-api@example.com",
        headers=operator_headers,
    )
    WorkActivityService(session).record_event(
        user_id=UUID(user["id"]),
        paper_id=None,
        activity_type=WorkActivityType.NOTE_SAVED,
        summary="Saved a local draft note.",
        happened_at=utcnow() - timedelta(days=1, hours=1),
        source=WorkActivitySource.API,
    )
    session.commit()

    response = client.post(f"/pulse/preview/{user['id']}", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    yesterday_candidate = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["card_type"] == PulseCardType.YESTERDAY_SUMMARY
    )
    assert yesterday_candidate["candidate_metadata"]["summary_date"]
    assert yesterday_candidate["candidate_metadata"]["total_events"] == 1
    assert yesterday_candidate["score_breakdown"]["total"] >= 10


def test_run_endpoint_persists_yesterday_summary_card(
    client,
    operator_headers,
    session,
) -> None:
    user = create_api_user(
        client,
        email="yesterday-run-api@example.com",
        headers=operator_headers,
    )
    WorkActivityService(session).record_event(
        user_id=UUID(user["id"]),
        paper_id=None,
        activity_type=WorkActivityType.RESPONSE_LETTER_GENERATED,
        summary="Generated a response-letter draft.",
        happened_at=utcnow() - timedelta(days=1, hours=2),
        source=WorkActivitySource.API,
    )
    session.commit()

    response = client.post(f"/pulse/run/{user['id']}", headers=operator_headers)

    assert response.status_code == 200
    payload = response.json()
    yesterday_card = next(
        card for card in payload["cards"] if card["card_type"] == PulseCardType.YESTERDAY_SUMMARY
    )
    assert yesterday_card["source_paper_id"] is None
    assert yesterday_card["candidate_metadata"]["summary_date"]


def test_preview_endpoint_exposes_today_suggestion_details(
    client,
    operator_headers,
    viewer_headers,
) -> None:
    user = create_api_user(
        client,
        email="today-preview-api@example.com",
        headers=operator_headers,
    )
    paper = create_api_paper(
        client,
        user_id=user["id"],
        title="Today Preview Paper",
        headers=operator_headers,
        paper_type=PaperType.REVISION,
        stage="revision",
        next_action="Finish the reviewer response appendix.",
        priority=5,
        last_touch_at=(utcnow() - timedelta(days=6)).isoformat(),
    )

    response = client.post(f"/pulse/preview/{user['id']}", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    today_candidate = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["card_type"] == PulseCardType.TODAY_SUGGESTION
    )
    assert today_candidate["source_paper_id"] == paper["id"]
    assert today_candidate["candidate_metadata"]["suggestion_kind"] == "execute_next_action"
    assert today_candidate["score_breakdown"]["total"] >= 10


def test_run_endpoint_persists_today_suggestion_card(
    client,
    operator_headers,
) -> None:
    user = create_api_user(
        client,
        email="today-run-api@example.com",
        headers=operator_headers,
    )
    paper = create_api_paper(
        client,
        user_id=user["id"],
        title="Today Run Paper",
        headers=operator_headers,
        paper_type=PaperType.UNDER_REVIEW,
        stage="under_review",
        next_action="Reply to the open reviewer methods question.",
        priority=4,
        last_touch_at=(utcnow() - timedelta(days=5)).isoformat(),
    )

    response = client.post(f"/pulse/run/{user['id']}", headers=operator_headers)

    assert response.status_code == 200
    payload = response.json()
    today_card = next(
        card for card in payload["cards"] if card["card_type"] == PulseCardType.TODAY_SUGGESTION
    )
    assert today_card["source_paper_id"] == paper["id"]
    assert today_card["candidate_metadata"]["suggestion_kind"] == "execute_next_action"


def test_preview_endpoint_exposes_related_paper_details_without_executing_retrieval(
    client,
    operator_headers,
    viewer_headers,
    session,
    monkeypatch,
) -> None:
    user = create_api_user(
        client,
        email="related-preview-api@example.com",
        headers=operator_headers,
    )
    paper = create_api_paper(
        client,
        user_id=user["id"],
        title="Related Preview Anchor",
        headers=operator_headers,
        paper_type=PaperType.PUBLISHED,
        stage="published",
        next_action=None,
        last_touch_at=(utcnow() - timedelta(days=1)).isoformat(),
    )
    create_completed_related_record(
        session,
        user_id=user["id"],
        paper_id=paper["id"],
        title="Preview Related Paper",
    )
    monkeypatch.setattr(
        external_retrieval_module,
        "create_external_retrieval_http_client",
        lambda _settings: (_ for _ in ()).throw(AssertionError("retrieval should not execute")),
    )

    response = client.post(f"/pulse/preview/{user['id']}", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    related_candidate = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["card_type"] == PulseCardType.RELATED_PAPER
    )
    assert related_candidate["source_paper_id"] == paper["id"]
    assert related_candidate["candidate_metadata"]["linked_paper_title"] == paper["title"]
    assert related_candidate["candidate_metadata"]["external_reference_key"].startswith("doi:")
    assert related_candidate["score_breakdown"]["total"] >= 10


def test_run_endpoint_persists_related_paper_card_without_executing_retrieval(
    client,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    user = create_api_user(
        client,
        email="related-run-api@example.com",
        headers=operator_headers,
    )
    paper = create_api_paper(
        client,
        user_id=user["id"],
        title="Related Run Anchor",
        headers=operator_headers,
        paper_type=PaperType.PUBLISHED,
        stage="published",
        next_action=None,
        last_touch_at=(utcnow() - timedelta(days=1)).isoformat(),
    )
    create_completed_related_record(
        session,
        user_id=user["id"],
        paper_id=paper["id"],
        title="Run Related Paper",
        doi="10.1234/run-related-paper",
        external_id="https://openalex.org/W1000",
    )
    monkeypatch.setattr(
        external_retrieval_module,
        "create_external_retrieval_http_client",
        lambda _settings: (_ for _ in ()).throw(AssertionError("retrieval should not execute")),
    )

    response = client.post(f"/pulse/run/{user['id']}", headers=operator_headers)

    assert response.status_code == 200
    payload = response.json()
    related_card = next(
        card for card in payload["cards"] if card["card_type"] == PulseCardType.RELATED_PAPER
    )
    assert related_card["source_paper_id"] == paper["id"]
    assert related_card["external_reference_key"] == "doi:10.1234/run-related-paper"
    assert related_card["candidate_metadata"]["linked_paper_title"] == paper["title"]
