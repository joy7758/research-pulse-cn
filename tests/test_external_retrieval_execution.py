from __future__ import annotations

from datetime import timedelta

import httpx

import research_pulse_cn.services.external_retrieval as external_retrieval_module
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import PaperType


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "External Retrieval Exec User",
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
            "source_links": ["https://example.local/papers/external-retrieval-exec"],
            "last_touch_at": (utcnow() - timedelta(days=2)).isoformat(),
            "next_action": "Draft revision notes",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


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
            "label": "Execution watch",
            "topics": ["Diffusion", "Alloy design"],
            "keywords": ["kinetics", "vacancy transport"],
            "venues": ["Acta Materialia", "JOM"],
            "authors_of_interest": ["Alice Zhang", "Bo Li"],
        },
    )
    assert watch_profile.status_code == 201


def enable_plan_only(monkeypatch) -> None:
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MODE", "plan_only")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES", "openalex,crossref,arxiv")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER", "6")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN", "4")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN", "3")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT", "7")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MAX_RESULTS_PER_PLAN", "3")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_EXECUTION_DEDUPE_MINUTES", "60")
    get_settings.cache_clear()


def enable_execute(monkeypatch) -> None:
    enable_plan_only(monkeypatch)
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MODE", "execute")
    get_settings.cache_clear()


def patch_http_client_factory(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        external_retrieval_module,
        "create_external_retrieval_http_client",
        lambda _settings: httpx.Client(transport=transport),
    )


def build_plans(client, headers, *, user_id: str) -> list[dict]:
    response = client.post(f"/external-retrieval/plans/build/{user_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["built_plans"]


def pick_plan(plans: list[dict], *, source_kind: str, retrieval_scope: str) -> dict:
    return next(
        item
        for item in plans
        if item["source_kind"] == source_kind and item["retrieval_scope"] == retrieval_scope
    )


def prepare_user_and_plans(
    client,
    headers,
    monkeypatch,
    *,
    mode: str,
    title: str,
) -> tuple[dict, dict, list[dict]]:
    if mode == "execute":
        enable_execute(monkeypatch)
    else:
        enable_plan_only(monkeypatch)
    user = create_user(client, headers, email=f"{title.replace(' ', '-').lower()}@example.com")
    paper = create_paper(client, headers, user_id=user["id"], title=title, venue="Acta Materialia")
    seed_retrieval_inputs(client, headers, user_id=user["id"], paper=paper)
    plans = build_plans(client, headers, user_id=user["id"])
    return user, paper, plans


def test_execute_is_blocked_when_mode_is_disabled(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    user, _paper, plans = prepare_user_and_plans(
        client,
        operator_headers,
        monkeypatch,
        mode="plan_only",
        title="Disabled Execute Paper",
    )
    plan = pick_plan(plans, source_kind="openalex", retrieval_scope="related_paper")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_MODE", "disabled")
    get_settings.cache_clear()

    response = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "external retrieval execution is disabled"


def test_execute_is_blocked_when_mode_is_plan_only(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    _user, _paper, plans = prepare_user_and_plans(
        client,
        operator_headers,
        monkeypatch,
        mode="plan_only",
        title="Plan Only Execute Paper",
    )
    plan = pick_plan(plans, source_kind="openalex", retrieval_scope="related_paper")

    response = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "external retrieval execution requires execute mode"


def test_openalex_execute_persists_normalized_results_and_results_endpoint(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    _user, paper, plans = prepare_user_and_plans(
        client,
        operator_headers,
        monkeypatch,
        mode="execute",
        title="OpenAlex Execute Paper",
    )
    plan = pick_plan(plans, source_kind="openalex", retrieval_scope="related_paper")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openalex.org"
        assert request.url.path == "/works"
        return httpx.Response(
            200,
            json={
                "meta": {"count": 1},
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "doi": "https://doi.org/10.1234/example-doi",
                        "display_name": "OpenAlex Example Result",
                        "publication_year": 2024,
                        "publication_date": "2024-02-01",
                        "abstract_inverted_index": {"Alloy": [0], "design": [1]},
                        "primary_location": {
                            "landing_page_url": "https://example.org/openalex-result",
                            "source": {"display_name": "Acta Materialia"},
                        },
                        "authorships": [
                            {
                                "author": {"display_name": "Alice Zhang"},
                                "author_position": "first",
                            }
                        ],
                    }
                ],
            },
        )

    patch_http_client_factory(monkeypatch, handler)

    execute = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )

    assert execute.status_code == 200
    payload = execute.json()
    assert payload["deduped"] is False
    assert payload["run"]["status"] == "completed"
    assert payload["run"]["raw_result_count"] == 1
    assert payload["run"]["normalized_result_count"] == 1
    assert payload["results"][0]["title"] == "OpenAlex Example Result"
    assert payload["results"][0]["source_title"] == "Acta Materialia"
    assert payload["results"][0]["doi"] == "10.1234/example-doi"
    assert payload["results"][0]["matched_reason_codes"] == [
        "recent_touched_paper_context",
        "watch_keywords_present",
        "watch_topics_present",
    ]

    results = client.get(
        f"/external-retrieval/results?run_id={payload['run']['id']}&plan_id={plan['id']}",
        headers=viewer_headers,
    )

    assert results.status_code == 200
    results_payload = results.json()
    assert len(results_payload) == 1
    assert results_payload[0]["external_id"] == "https://openalex.org/W123"
    assert results_payload[0]["title"] == "OpenAlex Example Result"
    assert results_payload[0]["raw_payload"]["display_name"] == "OpenAlex Example Result"


def test_crossref_execute_uses_polite_identification_when_configured(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    enable_execute(monkeypatch)
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_CROSSREF_MAILTO", "ops@example.com")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_CROSSREF_USER_AGENT_APP_NAME", "Research Pulse CN")
    get_settings.cache_clear()
    user = create_user(client, operator_headers, email="crossref-execute@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Crossref Execute Paper",
    )
    seed_retrieval_inputs(client, operator_headers, user_id=user["id"], paper=paper)
    plans = build_plans(client, operator_headers, user_id=user["id"])
    plan = pick_plan(plans, source_kind="crossref", retrieval_scope="related_paper")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.crossref.org"
        assert request.url.path == "/works"
        assert request.url.params["mailto"] == "ops@example.com"
        assert request.headers["User-Agent"] == "Research Pulse CN (mailto:ops@example.com)"
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "items": [
                        {
                            "DOI": "10.5678/crossref-example",
                            "URL": "https://doi.org/10.5678/crossref-example",
                            "title": ["Crossref Example Result"],
                            "container-title": ["JOM"],
                            "issued": {"date-parts": [[2025, 3, 1]]},
                            "author": [
                                {"given": "Bo", "family": "Li"},
                            ],
                            "abstract": "<jats:p>Compact abstract snippet.</jats:p>",
                        }
                    ]
                },
            },
        )

    patch_http_client_factory(monkeypatch, handler)

    execute = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )

    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run"]["status"] == "completed"
    assert payload["results"][0]["title"] == "Crossref Example Result"
    assert payload["results"][0]["abstract_snippet"] == "Compact abstract snippet."
    assert payload["results"][0]["authors"] == [{"name": "Bo Li"}]


def test_arxiv_execute_parses_atom_xml_and_normalizes_results(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    _user, _paper, plans = prepare_user_and_plans(
        client,
        operator_headers,
        monkeypatch,
        mode="execute",
        title="arXiv Execute Paper",
    )
    plan = pick_plan(plans, source_kind="arxiv", retrieval_scope="related_paper")

    atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2401.12345v1</id>
        <updated>2026-04-10T00:00:00Z</updated>
        <published>2026-04-09T00:00:00Z</published>
        <title>arXiv Example Result</title>
        <summary>Atom summary for deterministic normalization.</summary>
        <author><name>Alice Zhang</name></author>
        <arxiv:doi>10.9999/arxiv-example</arxiv:doi>
        <arxiv:journal_ref>arXiv</arxiv:journal_ref>
      </entry>
    </feed>"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "export.arxiv.org"
        assert request.url.path == "/api/query"
        assert "search_query" in request.url.params
        return httpx.Response(200, text=atom_xml)

    patch_http_client_factory(monkeypatch, handler)

    execute = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )

    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run"]["status"] == "completed"
    assert payload["results"][0]["external_id"] == "http://arxiv.org/abs/2401.12345v1"
    assert payload["results"][0]["title"] == "arXiv Example Result"
    assert payload["results"][0]["doi"] == "10.9999/arxiv-example"


def test_execute_dedupe_window_and_force_behavior(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    _user, _paper, plans = prepare_user_and_plans(
        client,
        operator_headers,
        monkeypatch,
        mode="execute",
        title="Dedupe Execute Paper",
    )
    plan = pick_plan(plans, source_kind="openalex", retrieval_scope="related_paper")
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        return httpx.Response(
            200,
            json={
                "meta": {"count": 1},
                "results": [
                    {
                        "id": f"https://openalex.org/W{call_count['value']}",
                        "display_name": f"Dedupe Result {call_count['value']}",
                        "publication_year": 2024,
                        "publication_date": "2024-02-01",
                        "primary_location": {
                            "landing_page_url": "https://example.org/dedupe",
                            "source": {"display_name": "JOM"},
                        },
                        "authorships": [],
                    }
                ],
            },
        )

    patch_http_client_factory(monkeypatch, handler)

    first = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )
    second = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )
    third = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}?force=true",
        headers=operator_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert call_count["value"] == 2
    assert first.json()["deduped"] is False
    assert second.json()["deduped"] is True
    assert first.json()["run"]["id"] == second.json()["run"]["id"]
    assert third.json()["deduped"] is False
    assert third.json()["run"]["id"] != first.json()["run"]["id"]


def test_provider_status_exposes_readiness_without_leaking_secrets(
    client,
    viewer_headers,
    monkeypatch,
) -> None:
    enable_execute(monkeypatch)
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_OPENALEX_API_KEY", "secret-openalex-key")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_CROSSREF_MAILTO", "ops@example.com")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_CROSSREF_USER_AGENT_APP_NAME", "Research Pulse CN")
    get_settings.cache_clear()

    response = client.get("/external-retrieval/provider-status", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "execute"
    assert payload["readiness"] is True
    assert payload["safe_config_presence"] == {
        "has_openalex_api_key": True,
        "has_crossref_mailto": True,
        "has_crossref_user_agent_app_name": True,
    }
    serialized = response.text
    assert "secret-openalex-key" not in serialized
    assert "ops@example.com" not in serialized


def test_pulse_input_preview_includes_compact_execution_summary(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    _user, _paper, plans = prepare_user_and_plans(
        client,
        operator_headers,
        monkeypatch,
        mode="execute",
        title="Pulse Input Execute Paper",
    )
    plan = pick_plan(plans, source_kind="openalex", retrieval_scope="related_paper")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "meta": {"count": 1},
                "results": [
                    {
                        "id": "https://openalex.org/W999",
                        "display_name": "Preview Summary Result",
                        "publication_year": 2024,
                        "publication_date": "2024-02-01",
                        "primary_location": {
                            "landing_page_url": "https://example.org/preview-summary",
                            "source": {"display_name": "JOM"},
                        },
                        "authorships": [],
                    }
                ],
            },
        )

    patch_http_client_factory(monkeypatch, handler)
    execute = client.post(
        f"/external-retrieval/plans/execute/{plan['id']}",
        headers=operator_headers,
    )
    assert execute.status_code == 200

    preview = client.get(
        f"/pulse/input-preview/{execute.json()['run']['user_id']}",
        headers=viewer_headers,
    )

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["retrieval_input_preview"]["mode"] == "execute"
    assert payload["latest_retrieval_runs_summary"]["latest_runs"][0]["status"] == "completed"
    assert payload["latest_retrieval_runs_summary"]["completed_run_count"] >= 1
