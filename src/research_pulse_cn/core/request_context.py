"""Request and worker logging context helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_PULSE_JOB_ID: ContextVar[str] = ContextVar("pulse_job_id", default="-")
_DELIVERY_JOB_ID: ContextVar[str] = ContextVar("delivery_job_id", default="-")
_DIGEST_ISSUE_ID: ContextVar[str] = ContextVar("digest_issue_id", default="-")
_MINI_GRANT_ID: ContextVar[str] = ContextVar("mini_grant_id", default="-")
_USER_ID: ContextVar[str] = ContextVar("user_id", default="-")
_WORKER_ROLE: ContextVar[str] = ContextVar("worker_role", default="-")
_CLIENT_DEVICE_ID: ContextVar[str] = ContextVar("client_device_id", default="-")


def get_request_id() -> str:
    """Return the active request id, if any."""
    return _REQUEST_ID.get()


def current_log_context() -> dict[str, str]:
    """Return the active logging context as serializable strings."""
    return {
        "request_id": _REQUEST_ID.get(),
        "pulse_job_id": _PULSE_JOB_ID.get(),
        "delivery_job_id": _DELIVERY_JOB_ID.get(),
        "digest_issue_id": _DIGEST_ISSUE_ID.get(),
        "mini_grant_id": _MINI_GRANT_ID.get(),
        "user_id": _USER_ID.get(),
        "worker_role": _WORKER_ROLE.get(),
        "client_device_id": _CLIENT_DEVICE_ID.get(),
    }


@contextmanager
def bind_log_context(**values: Any) -> Iterator[None]:
    """Temporarily bind request or worker identifiers for logging."""
    mapping: dict[str, ContextVar[str]] = {
        "request_id": _REQUEST_ID,
        "pulse_job_id": _PULSE_JOB_ID,
        "delivery_job_id": _DELIVERY_JOB_ID,
        "digest_issue_id": _DIGEST_ISSUE_ID,
        "mini_grant_id": _MINI_GRANT_ID,
        "user_id": _USER_ID,
        "worker_role": _WORKER_ROLE,
        "client_device_id": _CLIENT_DEVICE_ID,
    }
    tokens: list[tuple[ContextVar[str], Token[str]]] = []
    try:
        for key, value in values.items():
            context_var = mapping.get(key)
            if context_var is None or value is None:
                continue
            tokens.append((context_var, context_var.set(str(value))))
        yield
    finally:
        for context_var, token in reversed(tokens):
            context_var.reset(token)
