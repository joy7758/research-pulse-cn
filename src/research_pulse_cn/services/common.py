"""Shared service helpers."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import ConflictError


def commit_session(session: Session) -> None:
    """Commit the session and translate persistence conflicts."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(str(exc.orig or exc)) from exc
