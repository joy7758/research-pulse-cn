"""Official-account provider boundary, token cache, and transport implementations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Protocol

import httpx
from redis import Redis

from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.core.errors import ConflictError
from research_pulse_cn.core.metrics import MetricsRegistry, get_metrics
from research_pulse_cn.db.models import (
    DigestPublicationJob,
    PulseDigestIssue,
    WeChatIdentityBinding,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    DigestPublicationAttemptStatus,
    OfficialAccountProviderMode,
    OfficialAccountTransportKind,
)

logger = logging.getLogger(__name__)

WECHAT_OFFICIAL_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_TEMPLATE_NOTICE_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send"
DEFAULT_TEMPLATE_FIELD_MAPPING = {
    "issue_title": "first",
    "issue_date": "keyword1",
    "highlight_count": "keyword2",
    "summary": "keyword3",
    "remark": "remark",
}


@dataclass(slots=True)
class OfficialAccountPublishResult:
    """Outcome from a provider-boundary dispatch call."""

    provider_name: str
    provider_mode: OfficialAccountProviderMode
    attempt_status: DigestPublicationAttemptStatus
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    external_message_id: str | None = None
    error_summary: str | None = None
    provider_response_code: str | None = None
    provider_response_message: str | None = None


@dataclass(slots=True)
class CachedOfficialAccountToken:
    access_token: str
    expires_at: datetime
    last_refresh_at: datetime


@dataclass(slots=True)
class TokenCacheSnapshot:
    backend: str
    token_cached: bool
    token_expires_at: datetime | None
    last_refresh_at: datetime | None


@dataclass(slots=True)
class OfficialAccountTransportResult:
    success: bool
    request_payload: dict[str, Any]
    response_payload: dict[str, Any] | None
    external_message_id: str | None = None
    error_summary: str | None = None
    provider_response_code: str | None = None
    provider_response_message: str | None = None


class OfficialAccountPublisher(Protocol):
    """Provider-ready dispatch boundary for official-account publication."""

    provider_name: str
    provider_mode: OfficialAccountProviderMode

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        """Dispatch or preview a publication job."""


class OfficialAccountTransport(Protocol):
    """Transport strategy for outbound official-account sends."""

    transport_kind: OfficialAccountTransportKind

    def send(
        self,
        *,
        access_token: str,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountTransportResult:
        """Send one provider request for one bound recipient."""


class _InMemoryOfficialAccountTokenCache:
    def __init__(self) -> None:
        self._lock = Lock()
        self._tokens: dict[str, CachedOfficialAccountToken] = {}

    def get(self, cache_key: str) -> CachedOfficialAccountToken | None:
        with self._lock:
            return self._tokens.get(cache_key)

    def set(self, cache_key: str, token: CachedOfficialAccountToken) -> None:
        with self._lock:
            self._tokens[cache_key] = token

    def clear(self) -> None:
        with self._lock:
            self._tokens.clear()


class _RedisOfficialAccountTokenCache:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Redis | None = None
        self._lock = Lock()

    def _get_client(self) -> Redis:
        with self._lock:
            if self._client is None:
                self._client = Redis.from_url(
                    self.settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=self.settings.official_account_http_connect_timeout_seconds,
                    socket_timeout=self.settings.official_account_http_read_timeout_seconds,
                )
            return self._client

    def get(self, cache_key: str) -> CachedOfficialAccountToken | None:
        raw_value = self._get_client().get(cache_key)
        if raw_value is None:
            return None
        payload = json.loads(raw_value)
        access_token = str(payload.get("access_token") or "")
        expires_at = _coerce_datetime(payload.get("expires_at"))
        last_refresh_at = _coerce_datetime(payload.get("last_refresh_at"))
        if not access_token or expires_at is None or last_refresh_at is None:
            return None
        return CachedOfficialAccountToken(
            access_token=access_token,
            expires_at=expires_at,
            last_refresh_at=last_refresh_at,
        )

    def set(self, cache_key: str, token: CachedOfficialAccountToken) -> None:
        ttl_seconds = max(
            1,
            int((_ensure_utc(token.expires_at) - utcnow()).total_seconds()),
        )
        payload = json.dumps(
            {
                "access_token": token.access_token,
                "expires_at": _ensure_utc(token.expires_at).isoformat(),
                "last_refresh_at": _ensure_utc(token.last_refresh_at).isoformat(),
            }
        )
        self._get_client().set(cache_key, payload, ex=ttl_seconds)


_IN_MEMORY_TOKEN_CACHE = _InMemoryOfficialAccountTokenCache()
_REDIS_TOKEN_CACHES: dict[str, _RedisOfficialAccountTokenCache] = {}
_REDIS_TOKEN_CACHE_LOCK = Lock()


def reset_official_account_runtime_state() -> None:
    """Reset module-level caches for isolated tests."""
    _IN_MEMORY_TOKEN_CACHE.clear()
    with _REDIS_TOKEN_CACHE_LOCK:
        _REDIS_TOKEN_CACHES.clear()


def create_official_account_http_client(settings: Settings) -> httpx.Client:
    """Create an HTTP client with conservative timeout defaults."""
    timeout = httpx.Timeout(
        connect=settings.official_account_http_connect_timeout_seconds,
        read=settings.official_account_http_read_timeout_seconds,
        write=settings.official_account_http_read_timeout_seconds,
        pool=settings.official_account_http_read_timeout_seconds,
    )
    return httpx.Client(timeout=timeout)


class OfficialAccountAccessTokenService:
    """Acquire and cache official-account access tokens without persisting them."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        metrics: MetricsRegistry | None = None,
        now_provider=None,
        http_client_factory=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.metrics = metrics or get_metrics()
        self.now_provider = now_provider or utcnow
        self.http_client_factory = http_client_factory or create_official_account_http_client

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a cached token or refresh it from the provider."""
        self._require_real_mode()
        if not force_refresh:
            entry = self._read_cache_entry()
            if entry is not None and self._is_cache_entry_valid(entry):
                return entry.access_token
        refreshed = self._refresh_from_provider()
        return refreshed.access_token

    def refresh_summary(self) -> dict[str, Any]:
        """Refresh the provider token and return safe cache state."""
        self.get_access_token(force_refresh=True)
        snapshot = self.cache_snapshot()
        return {
            "action": "refreshed",
            "mode": self.settings.official_account_provider_mode,
            "transport_kind": self.settings.official_account_transport_kind,
            "token_cached": snapshot.token_cached,
            "token_expires_at": snapshot.token_expires_at,
            "last_refresh_at": snapshot.last_refresh_at,
            "cache_backend": snapshot.backend,
        }

    def cache_snapshot(self) -> TokenCacheSnapshot:
        """Return safe cache state without exposing the token value."""
        entry, backend = self._load_cache_entry_with_backend()
        valid_entry = entry if entry is not None and self._is_cache_entry_valid(entry) else None
        return TokenCacheSnapshot(
            backend=backend,
            token_cached=valid_entry is not None,
            token_expires_at=None if valid_entry is None else _ensure_utc(valid_entry.expires_at),
            last_refresh_at=(
                None if valid_entry is None else _ensure_utc(valid_entry.last_refresh_at)
            ),
        )

    def _require_real_mode(self) -> None:
        if self.settings.official_account_provider_mode != OfficialAccountProviderMode.REAL:
            raise ConflictError("official-account provider mode is not set to real")
        if not self.settings.official_account_real_send_enabled:
            raise ConflictError("official-account real send is not enabled")
        if not self.settings.wechat_official_app_id or not self.settings.wechat_official_app_secret:
            raise ConflictError("official-account credentials are not configured")

    def _refresh_from_provider(self) -> CachedOfficialAccountToken:
        refreshed_at = self.now_provider()
        try:
            with self.http_client_factory(self.settings) as client:
                response = client.get(
                    WECHAT_OFFICIAL_TOKEN_URL,
                    params={
                        "grant_type": "client_credential",
                        "appid": self.settings.wechat_official_app_id,
                        "secret": self.settings.wechat_official_app_secret,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # pragma: no cover - network/client specifics vary
            self.metrics.increment("official_account_access_token_refresh_failed_total")
            raise RuntimeError("official-account access token refresh failed") from exc

        access_token = str(payload.get("access_token") or "")
        expires_in = int(payload.get("expires_in") or 0)
        if not access_token or expires_in <= 0 or int(payload.get("errcode") or 0) != 0:
            self.metrics.increment("official_account_access_token_refresh_failed_total")
            raise RuntimeError(
                "official-account access token refresh failed: "
                f"{payload.get('errmsg') or 'invalid provider response'}"
            )

        entry = CachedOfficialAccountToken(
            access_token=access_token,
            expires_at=_ensure_utc(refreshed_at) + timedelta(seconds=expires_in),
            last_refresh_at=_ensure_utc(refreshed_at),
        )
        self._store_cache_entry(entry)
        self.metrics.increment("official_account_access_token_refresh_total")
        return entry

    def _is_cache_entry_valid(self, entry: CachedOfficialAccountToken) -> bool:
        skew = timedelta(seconds=self.settings.official_account_access_token_refresh_skew_seconds)
        return _ensure_utc(entry.expires_at) - skew > _ensure_utc(self.now_provider())

    def _cache_key(self) -> str:
        return (
            "research_pulse_cn:official_account:access_token:"
            f"{self.settings.wechat_official_app_id or 'unknown'}"
        )

    def _read_cache_entry(self) -> CachedOfficialAccountToken | None:
        entry, _backend = self._load_cache_entry_with_backend()
        return entry

    def _load_cache_entry_with_backend(
        self,
    ) -> tuple[CachedOfficialAccountToken | None, str]:
        cache_key = self._cache_key()
        if self.settings.app_env != "test":
            redis_cache = _get_redis_token_cache(self.settings)
            try:
                redis_entry = redis_cache.get(cache_key)
            except Exception:
                logger.warning("official-account redis token cache unavailable", exc_info=True)
                fallback_entry = _IN_MEMORY_TOKEN_CACHE.get(cache_key)
                return fallback_entry, "redis_fallback_in_memory"
            if redis_entry is not None:
                return redis_entry, "redis"
        return _IN_MEMORY_TOKEN_CACHE.get(cache_key), "in_memory"

    def _store_cache_entry(self, entry: CachedOfficialAccountToken) -> None:
        cache_key = self._cache_key()
        if self.settings.app_env != "test":
            redis_cache = _get_redis_token_cache(self.settings)
            try:
                redis_cache.set(cache_key, entry)
                return
            except Exception:
                logger.warning("official-account redis token cache write failed", exc_info=True)
        _IN_MEMORY_TOKEN_CACHE.set(cache_key, entry)


class TemplateNoticeTransport:
    """Concrete real-mode transport using the official template-notice API."""

    transport_kind = OfficialAccountTransportKind.TEMPLATE_NOTICE

    def __init__(
        self,
        settings: Settings,
        *,
        http_client_factory=None,
    ) -> None:
        self.settings = settings
        self.http_client_factory = http_client_factory or create_official_account_http_client

    def send(
        self,
        *,
        access_token: str,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountTransportResult:
        request_payload = build_template_notice_payload(
            publication_job=publication_job,
            issue=issue,
            binding=binding,
            settings=self.settings,
        )
        max_attempts = max(1, self.settings.official_account_max_retries + 1)
        for _attempt in range(max_attempts):
            try:
                with self.http_client_factory(self.settings) as client:
                    response = client.post(
                        WECHAT_TEMPLATE_NOTICE_URL,
                        params={"access_token": access_token},
                        json=request_payload,
                    )
                    response.raise_for_status()
                    payload = response.json()
            except Exception as exc:  # pragma: no cover - network specifics vary
                logger.warning("official-account template notice send attempt failed", exc_info=exc)
                continue

            errcode = str(payload.get("errcode") or "0")
            errmsg = str(payload.get("errmsg") or "")
            if errcode == "0":
                external_message_id = payload.get("msgid") or payload.get("msg_id")
                return OfficialAccountTransportResult(
                    success=True,
                    request_payload=request_payload,
                    response_payload=payload,
                    external_message_id=(
                        None if external_message_id is None else str(external_message_id)
                    ),
                    provider_response_code=errcode,
                    provider_response_message=errmsg or "ok",
                )
            return OfficialAccountTransportResult(
                success=False,
                request_payload=request_payload,
                response_payload=payload,
                error_summary=errmsg or "official-account provider rejected template send",
                provider_response_code=errcode,
                provider_response_message=errmsg or None,
            )

        return OfficialAccountTransportResult(
            success=False,
            request_payload=request_payload,
            response_payload=None,
            error_summary="official-account transport request failed",
        )


class DryRunOfficialAccountPublisher:
    """Preview publication jobs without external network calls."""

    provider_name = "wechat_official_account_dry_run"
    provider_mode = OfficialAccountProviderMode.DRY_RUN

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        request_payload = build_official_account_payload(
            publication_job=publication_job,
            issue=issue,
            binding=binding,
            settings=self.settings,
        )
        response_payload = {
            "status": "previewed",
            "provider_name": self.provider_name,
            "provider_mode": self.provider_mode.value,
            "transport_kind": self.settings.official_account_transport_kind.value,
            "external_send_enabled": False,
            "preview_landing_path": issue.deep_link_path,
        }
        return OfficialAccountPublishResult(
            provider_name=self.provider_name,
            provider_mode=self.provider_mode,
            attempt_status=DigestPublicationAttemptStatus.PREVIEWED,
            request_payload=request_payload,
            response_payload=response_payload,
        )


class DisabledOfficialAccountPublisher:
    """Block dispatch while keeping the provider boundary explicit."""

    provider_name = "wechat_official_account_disabled"
    provider_mode = OfficialAccountProviderMode.DISABLED

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        raise ConflictError("official-account provider mode is disabled")


class RealOfficialAccountPublisher:
    """Dispatch official-account publication jobs through a real provider transport."""

    provider_name = "wechat_official_account_real_template_notice"
    provider_mode = OfficialAccountProviderMode.REAL

    def __init__(
        self,
        settings: Settings,
        *,
        access_token_service: OfficialAccountAccessTokenService | None = None,
        transport: OfficialAccountTransport | None = None,
    ) -> None:
        self.settings = settings
        self.access_token_service = access_token_service or OfficialAccountAccessTokenService(
            settings
        )
        self.transport = transport or TemplateNoticeTransport(settings)

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        require_real_dispatch_ready(self.settings)
        request_payload: dict[str, Any] | None = None
        try:
            access_token = self.access_token_service.get_access_token()
            transport_result = self.transport.send(
                access_token=access_token,
                publication_job=publication_job,
                issue=issue,
                binding=binding,
            )
            request_payload = transport_result.request_payload
        except ConflictError:
            raise
        except Exception as exc:  # pragma: no cover - defensive fallback
            return OfficialAccountPublishResult(
                provider_name=self.provider_name,
                provider_mode=self.provider_mode,
                attempt_status=DigestPublicationAttemptStatus.FAILED,
                request_payload=request_payload,
                response_payload=None,
                error_summary=str(exc),
            )
        attempt_status = (
            DigestPublicationAttemptStatus.SENT
            if transport_result.success
            else DigestPublicationAttemptStatus.FAILED
        )
        return OfficialAccountPublishResult(
            provider_name=self.provider_name,
            provider_mode=self.provider_mode,
            attempt_status=attempt_status,
            request_payload=transport_result.request_payload,
            response_payload=transport_result.response_payload,
            external_message_id=transport_result.external_message_id,
            error_summary=transport_result.error_summary,
            provider_response_code=transport_result.provider_response_code,
            provider_response_message=transport_result.provider_response_message,
        )


def build_official_account_payload(
    *,
    publication_job: DigestPublicationJob,
    issue: PulseDigestIssue,
    binding: WeChatIdentityBinding,
    settings: Settings,
) -> dict[str, Any]:
    """Build a provider-ready, transport-neutral digest payload."""
    deep_link_path = issue.deep_link_path
    article_url = None
    if deep_link_path and settings.official_account_default_article_base_url:
        article_url = (
            settings.official_account_default_article_base_url.rstrip("/") + deep_link_path
        )

    highlights = []
    for item in issue.items[:3]:
        highlights.append(
            {
                "sort_order": item.sort_order,
                "pulse_card_id": str(item.pulse_card_id),
                "card_type": item.card_type.value,
                "source_paper_id": (
                    None if item.source_paper_id is None else str(item.source_paper_id)
                ),
                "title": item.title,
                "summary": item.summary,
                "why_now": item.why_now,
            }
        )

    return {
        "publication_job_id": str(publication_job.id),
        "digest_issue_id": str(issue.id),
        "title": issue.title,
        "summary": issue.summary,
        "issue_date": issue.issue_date.isoformat(),
        "highlight_count": issue.highlight_count,
        "selected_card_count": issue.selected_card_count,
        "highlights": highlights,
        "landing": {
            "deep_link_path": deep_link_path,
            "mini_program_app_id": settings.official_account_default_mini_program_app_id,
            "mini_program_path": None if deep_link_path is None else deep_link_path.lstrip("/"),
            "article_url": article_url,
        },
        "binding": {
            "binding_id": str(binding.id),
            "channel_type": binding.channel_type.value,
            "app_id": binding.app_id,
            "openid": binding.openid,
            "unionid": binding.unionid,
            "display_label": binding.display_label,
        },
        "provider_contract": {
            "publish_target": publication_job.publish_target.value,
            "publish_mode": publication_job.publish_mode.value,
            "provider_mode": settings.official_account_provider_mode.value,
            "transport_kind": settings.official_account_transport_kind.value,
            "dispatch_timeout_seconds": settings.official_account_dispatch_timeout_seconds,
            "external_send_enabled": official_account_outbound_send_enabled(settings),
        },
    }


def build_template_notice_payload(
    *,
    publication_job: DigestPublicationJob,
    issue: PulseDigestIssue,
    binding: WeChatIdentityBinding,
    settings: Settings,
) -> dict[str, Any]:
    """Build the concrete template-notice request payload for real dispatch."""
    base_payload = build_official_account_payload(
        publication_job=publication_job,
        issue=issue,
        binding=binding,
        settings=settings,
    )
    mapping = dict(settings.official_account_template_field_mapping_json or {})
    if not mapping:
        mapping = DEFAULT_TEMPLATE_FIELD_MAPPING

    logical_fields = _build_template_logical_fields(issue)
    data = {
        template_field: {"value": logical_fields[logical_field]}
        for logical_field, template_field in mapping.items()
        if logical_field in logical_fields and template_field
    }
    payload: dict[str, Any] = {
        "touser": binding.openid,
        "template_id": settings.wechat_official_digest_template_id,
        "data": data,
    }
    landing = base_payload["landing"]
    article_url = landing.get("article_url")
    mini_program_app_id = landing.get("mini_program_app_id")
    mini_program_path = landing.get("mini_program_path")
    if article_url:
        payload["url"] = article_url
    if mini_program_app_id and mini_program_path:
        payload["miniprogram"] = {
            "appid": mini_program_app_id,
            "pagepath": mini_program_path,
        }
    return payload


def build_provider_status(
    settings: Settings,
    *,
    access_token_service: OfficialAccountAccessTokenService,
) -> dict[str, Any]:
    """Build a safe provider status document for operators."""
    snapshot = access_token_service.cache_snapshot()
    readiness_checks = {
        "mode_not_disabled": settings.official_account_provider_mode
        != OfficialAccountProviderMode.DISABLED,
        "transport_supported": settings.official_account_transport_kind
        == OfficialAccountTransportKind.TEMPLATE_NOTICE,
        "app_id_configured": bool(settings.wechat_official_app_id),
        "app_secret_configured": bool(settings.wechat_official_app_secret),
        "digest_template_id_configured": bool(settings.wechat_official_digest_template_id),
        "real_send_enabled": bool(settings.official_account_real_send_enabled),
    }
    readiness_failures: list[str] = []
    if settings.official_account_provider_mode == OfficialAccountProviderMode.DISABLED:
        readiness_failures.append("provider mode is disabled")
    if not readiness_checks["transport_supported"]:
        readiness_failures.append("transport kind is not supported")
    if settings.official_account_provider_mode == OfficialAccountProviderMode.REAL:
        if not readiness_checks["app_id_configured"]:
            readiness_failures.append("wechat official app id is missing")
        if not readiness_checks["app_secret_configured"]:
            readiness_failures.append("wechat official app secret is missing")
        if not readiness_checks["digest_template_id_configured"]:
            readiness_failures.append("official-account digest template id is missing")
        if not readiness_checks["real_send_enabled"]:
            readiness_failures.append("real send is not enabled")
    readiness = not readiness_failures

    return {
        "mode": settings.official_account_provider_mode,
        "transport_kind": settings.official_account_transport_kind,
        "readiness": readiness,
        "readiness_checks": readiness_checks,
        "readiness_failures": readiness_failures,
        "callback_enabled": settings.official_account_callback_enabled,
        "real_send_enabled": settings.official_account_real_send_enabled,
        "dispatch_timeout_seconds": settings.official_account_dispatch_timeout_seconds,
        "http_connect_timeout_seconds": (settings.official_account_http_connect_timeout_seconds),
        "http_read_timeout_seconds": settings.official_account_http_read_timeout_seconds,
        "max_retries": settings.official_account_max_retries,
        "outbound_send_enabled": official_account_outbound_send_enabled(settings),
        "token_cached": snapshot.token_cached,
        "token_expires_at": snapshot.token_expires_at,
        "last_refresh_at": snapshot.last_refresh_at,
        "cache_backend": snapshot.backend,
        "has_app_id": bool(settings.wechat_official_app_id),
        "has_app_secret": bool(settings.wechat_official_app_secret),
        "has_digest_template_id": bool(settings.wechat_official_digest_template_id),
        "has_callback_token": bool(settings.wechat_official_callback_token),
        "has_callback_aes_key": bool(settings.wechat_official_callback_aes_key),
        "has_template_field_mapping": bool(settings.official_account_template_field_mapping_json),
        "default_mini_program_app_id": settings.official_account_default_mini_program_app_id,
        "default_article_base_url": settings.official_account_default_article_base_url,
        "callback_path": "/integrations/wechat/official-account/callback",
    }


def official_account_outbound_send_enabled(settings: Settings) -> bool:
    """Return whether real outbound send is explicitly enabled."""
    return (
        settings.official_account_provider_mode == OfficialAccountProviderMode.REAL
        and settings.official_account_real_send_enabled
    )


def require_real_dispatch_ready(settings: Settings) -> None:
    """Raise a conflict when real dispatch cannot safely run."""
    status = build_provider_status(
        settings,
        access_token_service=OfficialAccountAccessTokenService(settings),
    )
    if status["mode"] != OfficialAccountProviderMode.REAL:
        raise ConflictError("official-account provider mode is not set to real")
    if not status["readiness"]:
        raise ConflictError(
            "official-account provider is not ready: " + "; ".join(status["readiness_failures"])
        )


def get_official_account_publisher(
    settings: Settings,
    *,
    access_token_service: OfficialAccountAccessTokenService | None = None,
) -> OfficialAccountPublisher:
    """Return the configured official-account publisher implementation."""
    if settings.official_account_provider_mode == OfficialAccountProviderMode.DRY_RUN:
        return DryRunOfficialAccountPublisher(settings)
    if settings.official_account_provider_mode == OfficialAccountProviderMode.REAL:
        return RealOfficialAccountPublisher(
            settings,
            access_token_service=access_token_service,
        )
    return DisabledOfficialAccountPublisher()


def _build_template_logical_fields(issue: PulseDigestIssue) -> dict[str, str]:
    issue_date = issue.issue_date.isoformat()
    primary_action = "点击查看今日摘要"
    remark = primary_action
    if issue.deep_link_path:
        remark = f"{primary_action}，落地路径：{issue.deep_link_path}"
    return {
        "issue_title": _normalize_template_value(issue.title, limit=80),
        "issue_date": issue_date,
        "highlight_count": str(issue.highlight_count),
        "summary": _normalize_template_value(issue.summary, limit=120),
        "primary_action": _normalize_template_value(primary_action, limit=60),
        "remark": _normalize_template_value(remark, limit=120),
    }


def _normalize_template_value(value: str, *, limit: int) -> str:
    text = " ".join(value.strip().split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return _ensure_utc(parsed)


def _get_redis_token_cache(settings: Settings) -> _RedisOfficialAccountTokenCache:
    with _REDIS_TOKEN_CACHE_LOCK:
        cache = _REDIS_TOKEN_CACHES.get(settings.redis_url)
        if cache is None:
            cache = _RedisOfficialAccountTokenCache(settings)
            _REDIS_TOKEN_CACHES[settings.redis_url] = cache
        return cache
