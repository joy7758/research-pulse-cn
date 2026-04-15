"""Typed issuance objects for official-account binding handshake reserve."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class IssuedOfficialAccountBindingHandshakeSession:
    session_id: UUID
    plain_text_state_token: str
    expires_at: datetime | None
