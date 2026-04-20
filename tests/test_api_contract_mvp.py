from uuid import uuid4

from research_pulse_cn.app import create_app

MVP_PATH_METHODS: dict[str, set[str]] = {
    "/papers/import-preview": {"post"},
    "/papers/import-commit": {"post"},
    "/papers/progress": {"get"},
    "/papers/progress/summary": {"get"},
    "/papers/progress/pulse-context": {"get"},
    "/papers/{paper_id}/progress": {"get", "patch"},
    "/pulse/papers/daily": {"post"},
    "/pulse/papers/official-account/daily-summary": {"post"},
    "/pulse/papers/desktop-notification/draft": {"post"},
    "/pulse/papers/mini-program/detail/preview": {"post"},
}


def test_mvp_openapi_contains_core_paths_and_methods() -> None:
    openapi = create_app().openapi()
    paths = openapi["paths"]

    for path, methods in MVP_PATH_METHODS.items():
        assert path in paths
        assert methods <= set(paths[path])


def test_mvp_openapi_core_paths_keep_expected_success_status_codes() -> None:
    openapi = create_app().openapi()
    paths = openapi["paths"]

    assert "201" in paths["/papers/import-preview"]["post"]["responses"]
    assert "200" in paths["/papers/import-commit"]["post"]["responses"]
    assert "200" in paths["/papers/progress"]["get"]["responses"]
    assert "200" in paths["/papers/progress/summary"]["get"]["responses"]
    assert "200" in paths["/papers/progress/pulse-context"]["get"]["responses"]
    assert "200" in paths["/papers/{paper_id}/progress"]["get"]["responses"]
    assert "200" in paths["/papers/{paper_id}/progress"]["patch"]["responses"]
    assert "200" in paths["/pulse/papers/daily"]["post"]["responses"]
    assert "200" in paths["/pulse/papers/official-account/daily-summary"]["post"]["responses"]
    assert "200" in paths["/pulse/papers/desktop-notification/draft"]["post"]["responses"]
    assert "200" in paths["/pulse/papers/mini-program/detail/preview"]["post"]["responses"]


def test_progress_patch_validation_and_missing_paper_keep_minimal_error_contract(
    client,
    operator_headers,
    viewer_headers,
) -> None:
    invalid_patch = client.patch(
        f"/papers/{uuid4()}/progress",
        headers=operator_headers,
        json={"reading_status": "deep_reading"},
    )
    missing_detail = client.get(f"/papers/{uuid4()}/progress", headers=viewer_headers)

    assert invalid_patch.status_code == 422
    assert "detail" in invalid_patch.json()

    assert missing_detail.status_code == 404
    assert "detail" in missing_detail.json()
