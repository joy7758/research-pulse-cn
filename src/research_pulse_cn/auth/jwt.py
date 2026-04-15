"""Minimal HS256 JWT helpers for admin access tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from research_pulse_cn.core.errors import AuthenticationError


def encode_hs256_jwt(payload: dict[str, Any], secret: str) -> str:
    """Encode a compact HS256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_hs256_jwt(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
    expected_type: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Decode and validate a compact HS256 JWT."""
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", maxsplit=2)
    except ValueError as exc:
        raise AuthenticationError("invalid bearer token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64url_decode(encoded_signature), expected_signature):
        raise AuthenticationError("invalid bearer token")

    try:
        header = json.loads(_b64url_decode(encoded_header))
        payload = json.loads(_b64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AuthenticationError("invalid bearer token") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise AuthenticationError("invalid bearer token")
    if payload.get("iss") != issuer:
        raise AuthenticationError("token issuer mismatch")
    if payload.get("aud") != audience:
        raise AuthenticationError("token audience mismatch")
    if payload.get("type") != expected_type:
        raise AuthenticationError("token type mismatch")

    current_time = int((now or datetime.now(UTC)).timestamp())
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= current_time:
        raise AuthenticationError("token expired")

    return payload


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))
