"""Typed mini read-grant auth and issuance objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from research_pulse_cn.domain.enums import MiniReadGrantStatus, MiniReadGrantType


@dataclass(slots=True)
class MiniGrantContext:
    """Authenticated mini read-grant context for /mini endpoints only."""

    grant_id: UUID
    user_id: UUID
    binding_id: UUID | None
    digest_issue_id: UUID | None
    grant_type: MiniReadGrantType
    status: MiniReadGrantStatus
    scope: dict[str, Any]
    expires_at: datetime | None
    last_used_at: datetime | None


@dataclass(slots=True)
class IssuedMiniReadGrant:
    """Plaintext token material returned only when a grant is created."""

    grant_id: UUID
    plain_text_token: str
    expires_at: datetime | None
    preview_landing_path: str
