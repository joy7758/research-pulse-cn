"""Domain contracts for paper import parsing foundations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from research_pulse_cn.domain.enums import PaperImportSourceFormat

if TYPE_CHECKING:
    from research_pulse_cn.schemas.imports import PaperImportParseResult


class PaperImportParser(Protocol):
    """Detect and parse one supported paper import format."""

    source_format: PaperImportSourceFormat

    def may_match(self, payload: Any) -> bool:
        """Return whether the payload looks compatible with this parser."""

    def parse(self, payload: Any) -> PaperImportParseResult:
        """Parse one payload into normalized import records."""
