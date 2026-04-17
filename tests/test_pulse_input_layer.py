from datetime import timedelta
from uuid import UUID

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import PaperType, WorkActivitySource, WorkActivityType
from research_pulse_cn.services.work_activity import WorkActivityService


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Pulse Input User",
            "email": email,
            "field": "Materials",
            "interests": ["alloys"],
            "watched_topics": ["diffusion"],
            "watched_venues": ["JOM"],
            "reminder_preferences": {"timezone": "UTC"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_paper(client, headers, *, user_id: str, title: str, venue: str = "JOM") -> dict:
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": PaperType.REVISION,
            "stage": "revision",
            "venue": venue,
            "identifiers": {"authors": ["Alice Zhang", "Bo Li"]},
            "source_links": ["https://example.local/papers/pulse-input"],
            "last_touch_at": (utcnow() - timedelta(days=1, hours=1)).isoformat(),
            "next_action": "Prepare revision plan",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_bootstrap_watch_profile_from_paper_is_deterministic(
    client,
    operator_headers,
    viewer_headers,
) -> None:
    user = create_user(client, operator_headers, email="watch-bootstrap@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Pulse Bootstrap Paper",
    )

    bootstrap = client.post(
        f"/research-watch-profiles/bootstrap/{paper['id']}",
        headers=operator_headers,
    )
    listed = client.get(
        f"/research-watch-profiles?user_id={user['id']}",
        headers=viewer_headers,
    )

    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload["user_id"] == user["id"]
    assert payload["paper_id"] == paper["id"]
    assert payload["label"] == paper["title"]
    assert payload["source_mode"] == "paper_bootstrap"
    assert payload["keywords"] == [paper["title"]]
    assert payload["venues"] == [paper["venue"]]
    assert payload["authors_of_interest"] == ["Alice Zhang", "Bo Li"]
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == payload["id"]


def test_pulse_input_preview_returns_work_activity_summary_and_effective_watch_seeds(
    client,
    operator_headers,
    viewer_headers,
    session,
) -> None:
    user = create_user(client, operator_headers, email="pulse-input-preview@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Pulse Input Preview Paper",
        venue="Acta Materialia",
    )

    update_paper = client.put(
        f"/papers/{paper['id']}",
        headers=operator_headers,
        json={"priority": 5, "next_action": "Draft revised response"},
    )
    _preview_date, started_at, _ended_at = WorkActivityService(session).previous_day_window()
    WorkActivityService(session).record_event(
        user_id=UUID(user["id"]),
        paper_id=UUID(paper["id"]),
        activity_type=WorkActivityType.PAPER_UPDATED,
        summary="Updated paper priority for pulse input preview.",
        happened_at=started_at + timedelta(hours=1),
        source=WorkActivitySource.API,
    )
    session.commit()
    add_progress = client.post(
        f"/papers/{paper['id']}/progress-events",
        headers=operator_headers,
        json={
            "stage": "revision",
            "happened_at": (started_at + timedelta(hours=2)).isoformat(),
            "summary": "Prepared revised response outline.",
            "evidence_links": [],
            "owner": "operator",
        },
    )
    manual_profile = client.post(
        "/research-watch-profiles",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "paper_id": paper["id"],
            "label": "Manual watch seed",
            "topics": ["Diffusion", "diffusion", "Alloy design"],
            "keywords": ["Pulse Input Preview Paper", "kinetics"],
            "venues": ["Acta Materialia", "JOM"],
            "authors_of_interest": ["Alice Zhang", "alice zhang", "Bo Li"],
        },
    )
    bootstrap = client.post(
        f"/research-watch-profiles/bootstrap/{paper['id']}",
        headers=operator_headers,
    )

    session.commit()
    preview = client.get(
        f"/pulse/input-preview/{user['id']}",
        headers=viewer_headers,
    )

    assert update_paper.status_code == 200
    assert add_progress.status_code == 201
    assert manual_profile.status_code == 201
    assert bootstrap.status_code == 200
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["user_id"] == user["id"]
    assert payload["work_activity_summary"]["total_events"] >= 2
    assert payload["work_activity_summary"]["activity_type_counts"]["paper_updated"] >= 1
    assert payload["work_activity_summary"]["activity_type_counts"]["progress_event_created"] >= 1
    assert payload["work_activity_summary"]["touched_papers"][0]["paper_id"] == paper["id"]
    assert len(payload["enabled_watch_profiles"]) == 2
    assert payload["effective_watch_seeds"]["topics"] == ["Alloy design", "Diffusion"]
    assert payload["effective_watch_seeds"]["keywords"] == [
        "kinetics",
        "Pulse Input Preview Paper",
    ]
    assert payload["effective_watch_seeds"]["venues"] == ["Acta Materialia", "JOM"]
    assert payload["effective_watch_seeds"]["authors_of_interest"] == [
        "Alice Zhang",
        "Bo Li",
    ]
    assert payload["notes"]


def test_pulse_input_metrics_are_exposed(
    client,
    operator_headers,
    viewer_headers,
    internal_service_headers,
) -> None:
    user = create_user(client, operator_headers, email="pulse-input-metrics@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Pulse Metrics Paper",
    )

    client.put(
        f"/papers/{paper['id']}",
        headers=operator_headers,
        json={"priority": 5},
    )
    client.post(
        f"/research-watch-profiles/bootstrap/{paper['id']}",
        headers=operator_headers,
    )
    client.get(
        f"/pulse/input-preview/{user['id']}",
        headers=viewer_headers,
    )

    metrics = client.get("/ops/metrics", headers=internal_service_headers)

    assert metrics.status_code == 200
    body = metrics.text
    assert "work_activity_events_recorded_total " in body
    assert "research_watch_profiles_total " in body
    assert "pulse_input_previews_total " in body
