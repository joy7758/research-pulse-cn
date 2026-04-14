from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import PaperType, SignalSource, SubscriptionFrequency


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


def create_api_paper(client, *, user_id: str, title: str, headers: dict[str, str]):
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": PaperType.PUBLISHED,
            "stage": "published",
            "venue": "JOM",
            "identifiers": {},
            "source_links": [f"https://example.local/papers/{title.replace(' ', '-').lower()}"],
            "last_touch_at": (utcnow() - timedelta(days=14)).isoformat(),
            "next_action": "Check the latest signal delta",
            "priority": 4,
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
