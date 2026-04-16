"""Typed context objects for group workspace and result sharing grants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from research_pulse_cn.domain.enums import ResultShareGrantStatus, ResultShareKind


@dataclass(slots=True)
class IssuedResultShareGrant:
    grant_id: UUID
    plain_text_token: str
    expires_at: datetime | None


@dataclass(slots=True)
class ResultShareGrantContext:
    grant_id: UUID
    share_kind: ResultShareKind
    workspace_id: UUID | None
    digest_issue_id: UUID | None
    paper_id: UUID | None
    status: ResultShareGrantStatus
    display_label: str | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
