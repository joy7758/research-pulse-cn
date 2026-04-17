"""Official-account webpage OAuth start and completion services."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import ConflictError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.domain.enums import OfficialAccountOAuthScope
from research_pulse_cn.services import official_account as official_account_provider
from research_pulse_cn.services.official_account_binding_handshake import (
    OfficialAccountBindingHandshakeService,
)

WECHAT_OFFICIAL_OAUTH_AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
WECHAT_OFFICIAL_OAUTH_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_OFFICIAL_OAUTH_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


class OfficialAccountOAuthService:
    """Build authorize URLs and complete official-account webpage OAuth safely."""

    def __init__(self, session: Session, *, now_provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider
        self.handshake_service = OfficialAccountBindingHandshakeService(
            session,
            now_provider=now_provider,
        )
        self.metrics = get_metrics()

    def oauth_status(self) -> dict[str, Any]:
        callback_base_configured = bool(
            (self.settings.official_account_oauth_callback_public_base_url or "").strip()
        )
        callback_path = self._callback_path()
        readiness_checks = {
            "oauth_enabled": self.settings.official_account_oauth_enabled,
            "app_id_configured": bool((self.settings.wechat_official_app_id or "").strip()),
            "app_secret_configured": bool((self.settings.wechat_official_app_secret or "").strip()),
            "callback_public_base_url_configured": callback_base_configured,
            "callback_path_configured": bool(callback_path),
        }
        notes: list[str] = []
        if not self.settings.official_account_oauth_enabled:
            notes.append("Official-account OAuth completion is disabled.")
        if not callback_base_configured:
            notes.append("OAuth callback public base URL is not configured.")
        return {
            "oauth_enabled": self.settings.official_account_oauth_enabled,
            "default_scope": self.settings.official_account_oauth_default_scope,
            "callback_public_base_url_configured": callback_base_configured,
            "callback_path": callback_path,
            "fetch_userinfo_when_scope_userinfo": (
                self.settings.official_account_oauth_fetch_userinfo_when_scope_userinfo
            ),
            "success_redirect_configured": bool(
                (self.settings.official_account_oauth_success_redirect_url or "").strip()
            ),
            "failure_redirect_configured": bool(
                (self.settings.official_account_oauth_failure_redirect_url or "").strip()
            ),
            "readiness_checks": readiness_checks,
            "readiness_failures": [key for key, passed in readiness_checks.items() if not passed],
            "notes": notes,
        }

    def start_self_service_oauth(
        self,
        *,
        grant_id: UUID,
        user_id: UUID,
        app_id: str | None = None,
        display_label: str | None = None,
        requested_scope: OfficialAccountOAuthScope | None = None,
    ) -> dict[str, Any]:
        self._require_oauth_enabled()
        effective_app_id = self._resolve_app_id(app_id)
        self.handshake_service.supersede_active_sessions(
            user_id=user_id,
            app_id=effective_app_id,
        )
        session, _issued = self.handshake_service.create_self_service_session(
            grant_id=grant_id,
            user_id=user_id,
            app_id=effective_app_id,
            display_label=display_label,
        )
        return self._issue_authorize_url_payload(
            session_id=session.id,
            requested_scope=requested_scope,
            notes=[
                "Open the authorize URL in WeChat to continue official-account binding.",
                "OAuth completion does not create a generic app login session.",
            ],
        )

    def self_service_oauth_status(
        self,
        *,
        grant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        self.handshake_service._require_self_service_grant(grant_id, user_id=user_id)  # noqa: SLF001
        session = self.handshake_service.get_latest_session_for_oauth_status(
            user_id=user_id,
            self_service_grant_id=grant_id,
        )
        claimed_binding = None
        if session is not None and session.claimed_binding is not None:
            claimed_binding = self.handshake_service._safe_binding_summary(session.claimed_binding)  # noqa: SLF001
        return {
            "oauth_start_supported": True,
            "oauth_enabled": self.settings.official_account_oauth_enabled,
            "session": (
                None if session is None else self.handshake_service.serialize_session(session)
            ),
            "claimed_binding": claimed_binding,
            "notes": [
                (
                    "Official-account OAuth start is enabled."
                    if self.settings.official_account_oauth_enabled
                    else "Official-account OAuth start is configured off right now."
                )
            ],
        }

    def issue_authorize_url_for_session(
        self,
        session_id: UUID,
        *,
        requested_scope: OfficialAccountOAuthScope | None = None,
    ) -> dict[str, Any]:
        self._require_oauth_enabled()
        return self._issue_authorize_url_payload(
            session_id=session_id,
            requested_scope=requested_scope,
            notes=["Authorize URL was issued for an existing handshake session."],
        )

    def complete_callback(
        self,
        *,
        code: str,
        state: str,
    ) -> dict[str, Any]:
        self._require_oauth_enabled()
        if not code.strip():
            raise ValidationFailedError("official-account OAuth callback code is required")
        if not state.strip():
            raise ValidationFailedError("official-account OAuth callback state is required")

        session = self.handshake_service.get_session_by_state_token(state)
        self.handshake_service._validate_session_for_oauth_completion(session)  # noqa: SLF001
        self._validate_session_app_id(session.app_id)

        with bind_log_context(user_id=session.user_id, session_id=session.id):
            self.metrics.increment("official_account_oauth_callbacks_received_total")
            try:
                exchange_payload = self._exchange_code_for_identity(code=code)
            except Exception as exc:
                self.handshake_service.mark_session_failed(
                    session.id,
                    error_message=str(exc),
                )
                self.metrics.increment("official_account_oauth_exchange_failed_total")
                raise

            authorized_scope = self._coerce_scope(
                exchange_payload.get("scope"),
                fallback=session.requested_scope,
            )
            openid = str(exchange_payload.get("openid") or "").strip()
            if not openid:
                self.handshake_service.mark_session_failed(
                    session.id,
                    error_message="official-account OAuth exchange did not return an openid",
                    authorized_scope=authorized_scope,
                )
                self.metrics.increment("official_account_oauth_exchange_failed_total")
                raise ConflictError("official-account OAuth exchange did not return an openid")

            unionid = exchange_payload.get("unionid")
            userinfo_payload: dict[str, Any] | None = None
            try:
                if (
                    authorized_scope == OfficialAccountOAuthScope.SNSAPI_USERINFO
                    and self.settings.official_account_oauth_fetch_userinfo_when_scope_userinfo
                ):
                    userinfo_payload = self._fetch_userinfo(
                        access_token=str(exchange_payload.get("access_token") or ""),
                        openid=openid,
                    )
                    if unionid in (None, ""):
                        unionid = userinfo_payload.get("unionid")
            except Exception as exc:
                self.handshake_service.mark_session_failed(
                    session.id,
                    error_message=str(exc),
                    openid=openid,
                    authorized_scope=authorized_scope,
                )
                self.metrics.increment("official_account_oauth_exchange_failed_total")
                raise

            try:
                result = self.handshake_service.complete_session_from_oauth(
                    session.id,
                    authorized_scope=authorized_scope,
                    openid=openid,
                    unionid=None if unionid in (None, "") else str(unionid),
                    userinfo=userinfo_payload,
                )
            except ConflictError:
                self.metrics.increment("official_account_oauth_exchange_failed_total")
                raise

            self.metrics.increment("official_account_oauth_exchange_success_total")
            return {
                "action": "claimed",
                "session": result["session"],
                "claimed_binding": result["claimed_binding"],
                "callback_event": result["callback_event"],
                "callback_evidence_linked": result["callback_evidence_linked"],
                "authorized_scope": authorized_scope,
                "userinfo_fetched": userinfo_payload is not None,
            }

    def get_safe_session_for_state(self, state: str) -> dict[str, Any] | None:
        try:
            session = self.handshake_service.get_session_by_state_token(state)
        except Exception:
            return None
        return self.handshake_service.serialize_session(session)

    def _issue_authorize_url_payload(
        self,
        *,
        session_id: UUID,
        requested_scope: OfficialAccountOAuthScope | None,
        notes: list[str],
    ) -> dict[str, Any]:
        scope = requested_scope or self.settings.official_account_oauth_default_scope
        session = self.handshake_service.get_session(session_id)
        self._validate_session_app_id(session.app_id)
        session, raw_state_token = self.handshake_service.issue_authorize_state(
            session.id,
            requested_scope=scope,
        )
        authorize_url = self._build_authorize_url(
            app_id=session.app_id,
            redirect_uri=self.build_callback_url(),
            scope=session.requested_scope,
            state_token=raw_state_token,
        )
        self.metrics.increment("official_account_oauth_authorize_urls_issued_total")
        return {
            "session": self.handshake_service.serialize_session(session),
            "authorize_url": authorize_url,
            "requested_scope": session.requested_scope,
            "expires_at": session.expires_at,
            "notes": notes,
        }

    def build_callback_url(self) -> str:
        base_url = (self.settings.official_account_oauth_callback_public_base_url or "").strip()
        if not base_url:
            raise ConflictError("official-account OAuth callback public base URL is not configured")
        path = self._callback_path()
        return f"{base_url.rstrip('/')}{path}"

    def _callback_path(self) -> str:
        path = (self.settings.official_account_oauth_callback_path or "").strip()
        if not path:
            return ""
        return path if path.startswith("/") else f"/{path}"

    def _build_authorize_url(
        self,
        *,
        app_id: str,
        redirect_uri: str,
        scope: OfficialAccountOAuthScope,
        state_token: str,
    ) -> str:
        query = urlencode(
            {
                "appid": app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope.value,
                "state": state_token,
            }
        )
        return f"{WECHAT_OFFICIAL_OAUTH_AUTHORIZE_URL}?{query}#wechat_redirect"

    def _exchange_code_for_identity(self, *, code: str) -> dict[str, Any]:
        with official_account_provider.create_official_account_http_client(self.settings) as client:
            response = client.get(
                WECHAT_OFFICIAL_OAUTH_TOKEN_URL,
                params={
                    "appid": self.settings.wechat_official_app_id,
                    "secret": self.settings.wechat_official_app_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
        payload = self._decode_provider_json(response)
        if response.status_code >= 400 or payload.get("errcode") not in (None, 0, "0"):
            error_detail = payload.get("errmsg") or response.status_code
            raise ConflictError(f"official-account OAuth code exchange failed: {error_detail}")
        return payload

    def _fetch_userinfo(self, *, access_token: str, openid: str) -> dict[str, Any]:
        if not access_token:
            raise ConflictError("official-account OAuth userinfo fetch requires an access token")
        with official_account_provider.create_official_account_http_client(self.settings) as client:
            response = client.get(
                WECHAT_OFFICIAL_OAUTH_USERINFO_URL,
                params={
                    "access_token": access_token,
                    "openid": openid,
                    "lang": self.settings.official_account_oauth_lang,
                },
            )
        payload = self._decode_provider_json(response)
        if response.status_code >= 400 or payload.get("errcode") not in (None, 0, "0"):
            error_detail = payload.get("errmsg") or response.status_code
            raise ConflictError(f"official-account OAuth userinfo fetch failed: {error_detail}")
        return payload

    def _decode_provider_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ConflictError("official-account OAuth provider returned invalid JSON") from exc
        return payload if isinstance(payload, dict) else {}

    def _coerce_scope(
        self,
        raw_scope: Any,
        *,
        fallback: OfficialAccountOAuthScope,
    ) -> OfficialAccountOAuthScope:
        try:
            return OfficialAccountOAuthScope(str(raw_scope))
        except ValueError:
            return fallback

    def _require_oauth_enabled(self) -> None:
        if not self.settings.official_account_oauth_enabled:
            raise ConflictError("official-account OAuth completion is disabled")
        if not (self.settings.wechat_official_app_id or "").strip():
            raise ConflictError("official-account OAuth app_id is not configured")
        if not (self.settings.wechat_official_app_secret or "").strip():
            raise ConflictError("official-account OAuth app_secret is not configured")
        if not (self.settings.official_account_oauth_callback_public_base_url or "").strip():
            raise ConflictError("official-account OAuth callback public base URL is not configured")
        if not self._callback_path():
            raise ConflictError("official-account OAuth callback path is not configured")

    def _resolve_app_id(self, app_id: str | None) -> str:
        effective = (app_id or self.settings.wechat_official_app_id or "").strip()
        if not effective:
            raise ValidationFailedError("official-account OAuth app_id is required")
        return effective

    def _validate_session_app_id(self, session_app_id: str) -> None:
        configured = (self.settings.wechat_official_app_id or "").strip()
        if configured and configured != session_app_id:
            raise ConflictError(
                "configured official-account app_id does not match handshake session"
            )

    def now(self) -> datetime:
        if self.now_provider is None:
            return datetime.now(UTC)
        value = self.now_provider()
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
