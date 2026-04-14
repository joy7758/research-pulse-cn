"""Deterministic presentation-only progress read models."""

from research_pulse_cn.domain.enums import PaperType

PROGRESS_PERCENTAGE_BY_PAPER_TYPE: dict[PaperType, int] = {
    PaperType.PUBLISHED: 100,
    PaperType.REVISION: 80,
    PaperType.UNDER_REVIEW: 65,
    PaperType.IN_PREP: 35,
    PaperType.PAUSED: 0,
}


def derive_progress_percentage(paper_type: PaperType) -> int:
    """Return a read-model heuristic percentage for compact client views."""
    return PROGRESS_PERCENTAGE_BY_PAPER_TYPE[paper_type]
