"""Preview and commit services for normalized paper imports."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.domain.enums import PaperImportCommitRecordStatus, PaperType
from research_pulse_cn.domain.imports import PaperImportCommitter
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.imports import (
    PaperImportCommitRecordResult,
    PaperImportCommitRequest,
    PaperImportCommitResult,
    PaperImportPreviewCreateRequest,
    PaperImportPreviewRecord,
    PaperImportPreviewResult,
    PaperImportProblem,
    PaperImportRecord,
)
from research_pulse_cn.schemas.paper import PaperProfileCreate
from research_pulse_cn.services.import_formats import PaperImportFormatService
from research_pulse_cn.services.paper import PaperService


class PaperImportService:
    """Create import previews and commit selected records into paper profiles."""

    def __init__(
        self,
        session: Session | None = None,
        *,
        format_service: PaperImportFormatService | None = None,
        committer: PaperImportCommitter | None = None,
    ) -> None:
        self.session = session
        self.format_service = format_service or PaperImportFormatService()
        self.committer = committer or (
            _PaperProfileImportCommitter(session) if session is not None else None
        )
        self.user_repository = UserRepository(session) if session is not None else None

    def create_import_preview(
        self,
        request: PaperImportPreviewCreateRequest,
    ) -> PaperImportPreviewResult:
        parse_result = self.format_service.parse(
            request.payload,
            source_format=request.source_format,
        )
        records = [
            self._build_preview_record(record, source_index=index)
            for index, record in enumerate(parse_result.records, start=1)
        ]
        self._apply_batch_duplicate_warnings(records)
        preview_id = _build_preview_id(request.source_format.value, records)
        return PaperImportPreviewResult(
            preview_id=preview_id,
            source_format=request.source_format,
            created_at=datetime.now(UTC),
            total_records=len(records),
            valid_records_count=sum(1 for record in records if record.can_commit),
            warning_records_count=sum(1 for record in records if record.warnings),
            error_records_count=sum(1 for record in records if record.errors),
            records=records,
            warnings=parse_result.warnings,
            errors=parse_result.errors,
        )

    def commit_import_preview(
        self,
        request: PaperImportCommitRequest,
    ) -> PaperImportCommitResult:
        if self.committer is None:
            raise RuntimeError("paper import commit requires a persistence committer")
        if self.user_repository is not None and self.user_repository.get(request.user_id) is None:
            raise NotFoundError(f"user {request.user_id} was not found")

        preview_records = {record.source_index: record for record in request.preview_records}
        selected_indexes = _resolve_selected_source_indexes(
            request.preview_records, request.selected_source_indexes
        )

        result = PaperImportCommitResult(
            preview_id=request.preview_id,
            user_id=request.user_id,
            source_format=request.source_format,
            dry_run=request.dry_run,
            committed_at=datetime.now(UTC),
            total_selected=len(selected_indexes),
        )

        if not selected_indexes:
            result.warnings.append(
                _problem(
                    "no_selected_records",
                    "No importable preview records were selected for commit.",
                    "selected_source_indexes",
                )
            )
            return result

        for source_index in selected_indexes:
            preview_record = preview_records.get(source_index)
            if preview_record is None:
                missing_problem = _problem(
                    "selected_record_not_found",
                    "Selected source index was not present in the preview payload.",
                    f"records[{source_index}]",
                )
                result.record_results.append(
                    PaperImportCommitRecordResult(
                        source_index=source_index,
                        status=PaperImportCommitRecordStatus.FAILED,
                        reason="selected source index was not present in preview payload",
                        errors=[missing_problem],
                    )
                )
                result.errors.append(missing_problem)
                result.failed_count += 1
                continue

            if not preview_record.can_commit:
                result.record_results.append(
                    PaperImportCommitRecordResult(
                        source_index=source_index,
                        status=PaperImportCommitRecordStatus.SKIPPED,
                        reason="record is not importable",
                        warnings=preview_record.warnings,
                        errors=preview_record.errors,
                    )
                )
                result.skipped_count += 1
                continue

            if request.dry_run:
                result.record_results.append(
                    PaperImportCommitRecordResult(
                        source_index=source_index,
                        status=PaperImportCommitRecordStatus.DRY_RUN,
                        reason="dry run only; record was not persisted",
                        warnings=preview_record.warnings,
                        errors=[],
                    )
                )
                continue

            try:
                paper_id = self.committer.commit_imported_record(
                    user_id=request.user_id,
                    record=preview_record.normalized_record,
                    default_type=request.default_type,
                    default_stage=request.default_stage,
                    default_priority=request.default_priority,
                )
            except Exception as exc:
                result.record_results.append(
                    PaperImportCommitRecordResult(
                        source_index=source_index,
                        status=PaperImportCommitRecordStatus.FAILED,
                        reason=str(exc),
                        warnings=preview_record.warnings,
                        errors=[
                            _problem(
                                "commit_failed",
                                "Failed to persist the selected import record.",
                                f"records[{source_index}]",
                            )
                        ],
                    )
                )
                result.failed_count += 1
                continue

            result.committed_record_ids.append(paper_id)
            result.record_results.append(
                PaperImportCommitRecordResult(
                    source_index=source_index,
                    status=PaperImportCommitRecordStatus.COMMITTED,
                    reason="record committed",
                    paper_id=paper_id,
                    warnings=preview_record.warnings,
                    errors=[],
                )
            )
            result.committed_count += 1

        return result

    def _build_preview_record(
        self,
        record: PaperImportRecord,
        *,
        source_index: int,
    ) -> PaperImportPreviewRecord:
        normalized_record = record.model_copy(deep=True)
        warnings = list(normalized_record.warnings)
        errors = list(normalized_record.errors)
        if not normalized_record.title:
            errors.append(
                _problem(
                    "missing_required_field",
                    "Title is required before this record can be committed.",
                    "title",
                )
            )

        normalized_record.warnings = warnings
        normalized_record.errors = errors
        can_commit = not errors
        return PaperImportPreviewRecord(
            source_index=source_index,
            normalized_record=normalized_record,
            title=normalized_record.title,
            authors=list(normalized_record.authors),
            year=normalized_record.year,
            venue=normalized_record.venue,
            doi=normalized_record.doi,
            url=normalized_record.url,
            keywords=list(normalized_record.keywords),
            warnings=warnings,
            errors=errors,
            can_commit=can_commit,
            selected=can_commit,
        )

    def _apply_batch_duplicate_warnings(
        self,
        records: list[PaperImportPreviewRecord],
    ) -> None:
        doi_counts = Counter(
            normalized
            for normalized in (_normalize_doi_for_duplicate(record.doi) for record in records)
            if normalized
        )
        title_counts = Counter(
            normalized
            for normalized in (_normalize_title_for_duplicate(record.title) for record in records)
            if normalized
        )

        for record in records:
            duplicate_warnings: list[PaperImportProblem] = []
            normalized_doi = _normalize_doi_for_duplicate(record.doi)
            if normalized_doi and doi_counts[normalized_doi] > 1:
                duplicate_warnings.append(
                    _problem(
                        "duplicate_doi_in_batch",
                        "Another record in this batch uses the same DOI.",
                        "doi",
                    )
                )

            normalized_title = _normalize_title_for_duplicate(record.title)
            if normalized_title and title_counts[normalized_title] > 1:
                duplicate_warnings.append(
                    _problem(
                        "duplicate_title_in_batch",
                        "Another record in this batch uses the same normalized title.",
                        "title",
                    )
                )

            if not duplicate_warnings:
                continue

            record.warnings = [*record.warnings, *duplicate_warnings]
            record.normalized_record.warnings = [
                *record.normalized_record.warnings,
                *duplicate_warnings,
            ]


class _PaperProfileImportCommitter:
    """Commit one normalized record into the existing PaperProfile model."""

    def __init__(self, session: Session) -> None:
        self.paper_service = PaperService(session)

    def commit_imported_record(
        self,
        *,
        user_id: UUID,
        record: PaperImportRecord,
        default_type: PaperType,
        default_stage: str,
        default_priority: int,
    ) -> UUID:
        payload = PaperProfileCreate(
            user_id=user_id,
            title=record.title or "",
            title_zh=_select_localized_title(record.title, record.language, preferred="zh"),
            title_en=_select_localized_title(record.title, record.language, preferred="en"),
            type=default_type,
            stage=default_stage,
            venue=record.venue,
            identifiers=_build_import_identifiers(record),
            source_links=[record.url] if record.url else [],
            last_touch_at=datetime.now(UTC),
            next_action="Review imported paper metadata",
            blocker=None,
            priority=default_priority,
        )
        paper = self.paper_service.create_paper(payload)
        return paper.id


def _build_import_identifiers(record: PaperImportRecord) -> dict[str, Any]:
    identifiers: dict[str, Any] = {
        "import_source_format": record.source_format.value,
    }
    if record.doi:
        identifiers["doi"] = record.doi
    if record.source_identifier:
        identifiers["import_source_identifier"] = record.source_identifier
    if record.authors:
        identifiers["import_authors"] = list(record.authors)
    if record.keywords:
        identifiers["import_keywords"] = list(record.keywords)
    if record.language:
        identifiers["import_language"] = record.language
    if record.raw_source_payload:
        identifiers["import_raw_source_payload"] = record.raw_source_payload
    if record.attachments:
        identifiers["import_attachments"] = [item.model_dump() for item in record.attachments]
    if record.notes:
        identifiers["import_notes"] = [item.model_dump() for item in record.notes]
    return identifiers


def _select_localized_title(
    title: str | None, language: str | None, *, preferred: str
) -> str | None:
    if not title or not language:
        return None
    normalized_language = language.casefold()
    if preferred == "zh" and normalized_language.startswith("zh"):
        return title
    if preferred == "en" and normalized_language.startswith("en"):
        return title
    return None


def _problem(code: str, message: str, field: str | None = None) -> PaperImportProblem:
    return PaperImportProblem(code=code, message=message, field=field)


def _resolve_selected_source_indexes(
    preview_records: list[PaperImportPreviewRecord],
    explicit_indexes: list[int],
) -> list[int]:
    selected_indexes = explicit_indexes or [
        record.source_index for record in preview_records if record.selected
    ]
    seen: set[int] = set()
    ordered_indexes: list[int] = []
    for source_index in selected_indexes:
        if source_index in seen:
            continue
        seen.add(source_index)
        ordered_indexes.append(source_index)
    return ordered_indexes


def _normalize_doi_for_duplicate(doi: str | None) -> str | None:
    if not doi:
        return None
    return doi.strip().casefold()


def _normalize_title_for_duplicate(title: str | None) -> str | None:
    if not title:
        return None
    return " ".join(title.split()).casefold()


def _build_preview_id(source_format: str, records: list[PaperImportPreviewRecord]) -> str:
    digest_payload = {
        "source_format": source_format,
        "records": [
            {
                "source_index": record.source_index,
                "title": record.title,
                "doi": record.doi,
                "year": record.year,
                "source_identifier": record.normalized_record.source_identifier,
            }
            for record in records
        ],
    }
    encoded = json.dumps(digest_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]
