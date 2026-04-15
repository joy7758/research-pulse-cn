from datetime import timedelta

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import PaperType


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "External Retrieval User",
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
            "source_links": ["https://example.local/papers/external-retrieval"],
            "last_touch_at": (utcnow() - timedelta(days=2)).isoformat(),
            "next_action": "Draft revision notes",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def enable_plan_only(monkeypatch) -> None:
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MODE", "plan_only")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES", "openalex,crossref,arxiv")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER", "6")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN", "4")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN", "3")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT", "7")
    get_settings.cache_clear()


def seed_retrieval_inputs(client, headers, *, user_id: str, paper: dict) -> None:
    update_paper = client.put(
        f"/papers/{paper['id']}",
        headers=headers,
        json={"priority": 5, "next_action": "Review diffusion response outline"},
    )
    assert update_paper.status_code == 200
    watch_profile = client.post(
        "/research-watch-profiles",
        headers=headers,
        json={
            "user_id": user_id,
            "paper_id": paper["id"],
            "label": "Retrieval watch",
            "topics": ["Diffusion", "Alloy design", "Diffusion"],
            "keywords": ["kinetics", "vacancy transport"],
            "venues": ["Acta Materialia", "JOM"],
            "authors_of_interest": ["Alice Zhang", "Bo Li", "alice zhang"],
        },
    )
    assert watch_profile.status_code == 201


def test_external_retrieval_input_preview_returns_deterministic_effective_seeds(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    enable_plan_only(monkeypatch)
    user = create_user(client, operator_headers, email="external-preview@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="External Retrieval Paper",
        venue="Acta Materialia",
    )
    seed_retrieval_inputs(client, operator_headers, user_id=user["id"], paper=paper)

    preview = client.get(
        f"/external-retrieval/input-preview/{user['id']}",
        headers=viewer_headers,
    )

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["mode"] == "plan_only"
    assert payload["enabled_sources"] == ["openalex", "crossref", "arxiv"]
    assert payload["effective_retrieval_seeds"]["topics"] == ["Alloy design", "Diffusion"]
    assert payload["effective_retrieval_seeds"]["keywords"] == ["kinetics", "vacancy transport"]
    assert payload["effective_retrieval_seeds"]["venues"] == ["Acta Materialia", "JOM"]
    assert payload["effective_retrieval_seeds"]["authors_of_interest"] == [
        "Alice Zhang",
        "Bo Li",
    ]
    assert payload["effective_retrieval_seeds"]["touched_paper_titles"] == [
        "External Retrieval Paper"
    ]
    plan_map = {
        (item["source_kind"], item["retrieval_scope"]): item
        for item in payload["source_plan_previews"]
    }
    assert plan_map[("openalex", "related_paper")]["plan_label"] == "OpenAlex related papers"
    assert plan_map[("openalex", "related_paper")]["query_payload"]["topics"] == [
        "Alloy design",
        "Diffusion",
    ]
    assert plan_map[("crossref", "venue_update")]["plan_label"] == (
        "Crossref venue updates: Acta Materialia"
    )
    assert plan_map[("arxiv", "related_paper")]["query_payload"]["keywords"] == [
        "kinetics",
        "vacancy transport",
    ]


def test_external_retrieval_build_persists_plans_with_unique_plan_hash_semantics(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    enable_plan_only(monkeypatch)
    user = create_user(client, operator_headers, email="external-build@example.com")
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Build Paper")
    seed_retrieval_inputs(client, operator_headers, user_id=user["id"], paper=paper)

    first_build = client.post(
        f"/external-retrieval/plans/build/{user['id']}",
        headers=operator_headers,
    )
    second_build = client.post(
        f"/external-retrieval/plans/build/{user['id']}",
        headers=operator_headers,
    )
    listed = client.get(
        f"/external-retrieval/plans?user_id={user['id']}",
        headers=viewer_headers,
    )

    assert first_build.status_code == 200
    assert second_build.status_code == 200
    assert listed.status_code == 200
    first_payload = first_build.json()
    second_payload = second_build.json()
    listed_payload = listed.json()
    assert len(first_payload["built_plans"]) == 6
    assert len(second_payload["built_plans"]) == 6
    assert len(listed_payload) == 6
    assert len({item["plan_hash"] for item in listed_payload}) == 6


def test_external_retrieval_build_is_blocked_when_mode_is_disabled(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="external-disabled@example.com")

    response = client.post(
        f"/external-retrieval/plans/build/{user['id']}",
        headers=operator_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "external retrieval planning is disabled"


def test_pulse_input_preview_includes_compact_retrieval_planning_section(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    enable_plan_only(monkeypatch)
    user = create_user(client, operator_headers, email="external-pulse-preview@example.com")
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Pulse Preview Paper")
    seed_retrieval_inputs(client, operator_headers, user_id=user["id"], paper=paper)

    preview = client.get(
        f"/pulse/input-preview/{user['id']}",
        headers=viewer_headers,
    )

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["retrieval_input_preview"]["mode"] == "plan_only"
    assert payload["retrieval_input_preview"]["preview_plan_count"] == 6
    assert {
        item["source_kind"] for item in payload["retrieval_input_preview"]["source_plan_previews"]
    } == {
        "openalex",
        "crossref",
        "arxiv",
    }


def test_external_retrieval_metrics_are_exposed(
    client,
    operator_headers,
    viewer_headers,
    internal_service_headers,
    monkeypatch,
) -> None:
    enable_plan_only(monkeypatch)
    user = create_user(client, operator_headers, email="external-metrics@example.com")
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Metrics Paper")
    seed_retrieval_inputs(client, operator_headers, user_id=user["id"], paper=paper)

    client.get(f"/external-retrieval/input-preview/{user['id']}", headers=viewer_headers)
    client.post(f"/external-retrieval/plans/build/{user['id']}", headers=operator_headers)
    metrics = client.get("/ops/metrics", headers=internal_service_headers)

    assert metrics.status_code == 200
    body = metrics.text
    assert "external_retrieval_input_previews_total " in body
    assert "external_retrieval_plans_built_total " in body
    assert "external_retrieval_plans_persisted_total " in body
