from uuid import UUID, uuid4

from research_pulse_cn.domain.enums import (
    PaperImportCommitRecordStatus,
    PaperImportSourceFormat,
)
from research_pulse_cn.schemas.imports import (
    PaperImportCommitRequest,
    PaperImportPreviewCreateRequest,
)
from research_pulse_cn.services.paper_import import PaperImportService


class FakePaperImportCommitter:
    def __init__(self, *, fail_titles: set[str] | None = None) -> None:
        self.fail_titles = set(fail_titles or set())
        self.committed_titles: list[str] = []

    def commit_imported_record(
        self,
        *,
        user_id: UUID,
        record,
        default_type,
        default_stage,
        default_priority,
    ) -> UUID:
        if record.title in self.fail_titles:
            raise RuntimeError(f"failed to import {record.title}")
        self.committed_titles.append(record.title or "")
        return uuid4()


def create_user(client, headers, *, email: str = "import-user@example.com") -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Import User",
            "email": email,
            "field": "Materials",
            "interests": ["imports"],
            "watched_topics": ["metadata"],
            "watched_venues": ["Import Journal"],
            "reminder_preferences": {"timezone": "Asia/Shanghai"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_csl_json_preview_is_created() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.CSL_JSON,
            payload=[
                {
                    "title": "CSL Preview Record",
                    "author": [{"given": "Alice", "family": "Zhang"}],
                    "issued": {"date-parts": [[2024]]},
                }
            ],
        )
    )

    assert preview.total_records == 1
    assert preview.valid_records_count == 1
    assert preview.records[0].title == "CSL Preview Record"
    assert preview.records[0].can_commit is True


def test_bibtex_preview_is_created() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.BIBTEX,
            payload="""
            @article{zhang2024preview,
              title = {BibTeX Preview Record},
              author = {Alice Zhang and Bo Li},
              year = {2024},
              journal = {Import Journal}
            }
            """,
        )
    )

    assert preview.total_records == 1
    assert preview.records[0].authors == ["Alice Zhang", "Bo Li"]
    assert preview.records[0].venue == "Import Journal"


def test_ris_preview_is_created() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.RIS,
            payload="""
            TY  - JOUR
            TI  - RIS Preview Record
            AU  - Alice Zhang
            PY  - 2023
            JO  - RIS Journal
            ER  -
            """,
        )
    )

    assert preview.total_records == 1
    assert preview.records[0].title == "RIS Preview Record"
    assert preview.records[0].year == 2023


def test_chinese_tabular_preview_is_created() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.TABULAR,
            payload=(
                "标题\t作者\t发表年份\t来源\t摘要\t关键词\t链接\n"
                "中文导入记录\t张三；李四\t2022\t材料导报\t中文摘要\t导入；论文\t"
                "https://example.com/cn\n"
            ),
        )
    )

    assert preview.total_records == 1
    assert preview.records[0].title == "中文导入记录"
    assert preview.records[0].authors == ["张三", "李四"]


def test_pdf_folder_preview_is_created() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.PDF_FOLDER,
            payload=["papers/Research_Pulse_Import.pdf"],
        )
    )

    assert preview.total_records == 1
    assert preview.records[0].title == "Research Pulse Import"
    assert preview.records[0].warnings


def test_preview_counts_and_commitability_flags_are_correct() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.TABULAR,
            payload=("title,authors,year\nImportable Record,Alice Zhang,2024\n,Bo Li,2023\n"),
        )
    )

    assert preview.total_records == 2
    assert preview.valid_records_count == 1
    assert preview.warning_records_count == 1
    assert preview.error_records_count == 1
    assert preview.records[0].can_commit is True
    assert preview.records[1].can_commit is False
    assert {problem.code for problem in preview.records[1].errors} == {"missing_required_field"}


def test_warning_without_error_can_be_committed() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.CSL_JSON,
            payload=[{"title": "Warning Only Record", "issued": {"date-parts": [["bad"]]}}],
        )
    )

    assert preview.records[0].warnings
    assert preview.records[0].errors == []
    assert preview.records[0].can_commit is True


def test_batch_duplicate_warnings_are_added_for_doi_and_title() -> None:
    service = PaperImportService()

    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.CSL_JSON,
            payload=[
                {
                    "title": "Duplicate Title",
                    "DOI": "10.1000/dup",
                },
                {
                    "title": "duplicate   title",
                    "DOI": "10.1000/dup",
                },
            ],
        )
    )

    for record in preview.records:
        codes = {problem.code for problem in record.warnings}
        assert "duplicate_doi_in_batch" in codes
        assert "duplicate_title_in_batch" in codes


def test_commit_only_selected_source_indexes() -> None:
    committer = FakePaperImportCommitter()
    service = PaperImportService(committer=committer)
    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.CSL_JSON,
            payload=[
                {"title": "First Commit Record"},
                {"title": "Second Commit Record"},
            ],
        )
    )

    result = service.commit_import_preview(
        PaperImportCommitRequest(
            user_id=uuid4(),
            source_format=PaperImportSourceFormat.CSL_JSON,
            preview_id=preview.preview_id,
            preview_records=preview.records,
            selected_source_indexes=[2],
        )
    )

    assert result.total_selected == 1
    assert result.committed_count == 1
    assert committer.committed_titles == ["Second Commit Record"]


def test_commit_skips_non_importable_records_and_returns_reason() -> None:
    committer = FakePaperImportCommitter()
    service = PaperImportService(committer=committer)
    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.TABULAR,
            payload="title,authors\n,Missing title author\n",
        )
    )

    result = service.commit_import_preview(
        PaperImportCommitRequest(
            user_id=uuid4(),
            source_format=PaperImportSourceFormat.TABULAR,
            preview_id=preview.preview_id,
            preview_records=preview.records,
            selected_source_indexes=[1],
        )
    )

    assert result.committed_count == 0
    assert result.skipped_count == 1
    assert result.record_results[0].status == PaperImportCommitRecordStatus.SKIPPED
    assert result.record_results[0].reason == "record is not importable"


def test_commit_single_failure_does_not_break_batch() -> None:
    committer = FakePaperImportCommitter(fail_titles={"Broken Record"})
    service = PaperImportService(committer=committer)
    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.CSL_JSON,
            payload=[
                {"title": "Healthy Record"},
                {"title": "Broken Record"},
            ],
        )
    )

    result = service.commit_import_preview(
        PaperImportCommitRequest(
            user_id=uuid4(),
            source_format=PaperImportSourceFormat.CSL_JSON,
            preview_id=preview.preview_id,
            preview_records=preview.records,
            selected_source_indexes=[1, 2],
        )
    )

    assert result.committed_count == 1
    assert result.failed_count == 1
    assert result.record_results[0].status == PaperImportCommitRecordStatus.COMMITTED
    assert result.record_results[1].status == PaperImportCommitRecordStatus.FAILED


def test_commit_dry_run_returns_previewed_commit_result() -> None:
    committer = FakePaperImportCommitter()
    service = PaperImportService(committer=committer)
    preview = service.create_import_preview(
        PaperImportPreviewCreateRequest(
            source_format=PaperImportSourceFormat.CSL_JSON,
            payload=[{"title": "Dry Run Record"}],
        )
    )

    result = service.commit_import_preview(
        PaperImportCommitRequest(
            user_id=uuid4(),
            source_format=PaperImportSourceFormat.CSL_JSON,
            preview_id=preview.preview_id,
            preview_records=preview.records,
            selected_source_indexes=[1],
            dry_run=True,
        )
    )

    assert result.committed_count == 0
    assert result.failed_count == 0
    assert result.skipped_count == 0
    assert result.record_results[0].status == PaperImportCommitRecordStatus.DRY_RUN
    assert committer.committed_titles == []


def test_import_preview_and_commit_routes_persist_into_existing_paper_profile_model(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="import-route@example.com")
    preview_response = client.post(
        "/papers/import-preview",
        headers=operator_headers,
        json={
            "source_format": "csl_json",
            "payload": [
                {
                    "title": "Persisted Import Record",
                    "author": [{"given": "Alice", "family": "Zhang"}],
                    "issued": {"date-parts": [[2024]]},
                    "container-title": ["Import Journal"],
                    "DOI": "10.1000/persist.1",
                    "URL": "https://example.com/persist.1",
                    "keyword": "imports;preview",
                }
            ],
        },
    )

    assert preview_response.status_code == 201
    preview_payload = preview_response.json()
    assert preview_payload["valid_records_count"] == 1

    commit_response = client.post(
        "/papers/import-commit",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "source_format": "csl_json",
            "preview_id": preview_payload["preview_id"],
            "preview_records": preview_payload["records"],
            "selected_source_indexes": [1],
            "default_stage": "imported",
            "default_type": "published",
        },
    )

    assert commit_response.status_code == 200
    commit_payload = commit_response.json()
    assert commit_payload["committed_count"] == 1
    paper_id = commit_payload["committed_record_ids"][0]

    paper_response = client.get(f"/papers/{paper_id}", headers=operator_headers)
    assert paper_response.status_code == 200
    paper_payload = paper_response.json()
    assert paper_payload["title"] == "Persisted Import Record"
    assert paper_payload["stage"] == "imported"
    assert paper_payload["type"] == "published"
    assert paper_payload["identifiers"]["doi"] == "10.1000/persist.1"
    assert paper_payload["identifiers"]["import_source_format"] == "csl_json"
    assert paper_payload["identifiers"]["import_source_identifier"] == "10.1000/persist.1"
