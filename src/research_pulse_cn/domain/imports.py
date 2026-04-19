"""Domain contracts for paper import parsing and commit foundations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from research_pulse_cn.domain.enums import PaperImportSourceFormat, PaperType

if TYPE_CHECKING:
    from research_pulse_cn.schemas.imports import PaperImportParseResult, PaperImportRecord


class PaperImportParser(Protocol):
    """Detect and parse one supported paper import format."""

    source_format: PaperImportSourceFormat

    def may_match(self, payload: Any) -> bool:
        """Return whether the payload looks compatible with this parser."""

    def parse(self, payload: Any) -> PaperImportParseResult:
        """Parse one payload into normalized import records."""


class PaperImportCommitter(Protocol):
    """Persist one normalized import record into repository-owned paper models."""

    def commit_imported_record(
        self,
        *,
        user_id: UUID,
        record: PaperImportRecord,
        default_type: PaperType,
        default_stage: str,
        default_priority: int,
    ) -> UUID:
        """Commit one normalized record and return the created paper id."""
