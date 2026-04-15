"""Admin authentication and refresh token service."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token, verify_password
from research_pulse_cn.auth.jwt import decode_hs256_jwt, encode_hs256_jwt
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import AuthenticationError
from research_pulse_cn.db.models import AdminAccount, AdminRefreshToken, utcnow
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType
from research_pulse_cn.repositories.admin_account import AdminAccountRepository
from research_pulse_cn.repositories.admin_refresh_token import AdminRefreshTokenRepository
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.common import commit_session


@dataclass(slots=True)
class IssuedAdminTokens:
    access_token: str
    refresh_token: str
    expires_in_seconds: int
    admin_account: AdminAccount


class AuthService:
    """Authenticate admins and rotate server-revocable refresh tokens."""

    def __init__(
        self,
        session: Session,
        *,
        now_provider=None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.admin_repository = AdminAccountRepository(session)
        self.refresh_token_repository = AdminRefreshTokenRepository(session)
        self.audit_service = AuditService(session)

    def login(
        self,
        *,
        email: str,
        password: str,
        created_ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
    ) -> IssuedAdminTokens:
        admin_account = self.admin_repository.get_by_email(email)
        if admin_account is None or not verify_password(password, admin_account.password_hash):
            self.audit_service.safe_record(
                actor=ActorContext(
                    actor_type=AuditActorType.ANONYMOUS,
                    actor_label=email.lower(),
                ),
                action="auth.login_failure",
                resource_type="admin_account",
                request_id=request_id,
                route=route,
                method=method,
                status_code=401,
                metadata={"reason": "invalid_credentials"},
            )
            raise AuthenticationError("invalid email or password")
        if not admin_account.is_active:
            self.audit_service.safe_record(
                actor=ActorContext(
                    actor_type=AuditActorType.ADMIN,
                    actor_id=admin_account.id,
                    actor_label=admin_account.email,
                    admin_role=admin_account.role,
                    is_active=False,
                ),
                action="auth.login_failure",
                resource_type="admin_account",
                resource_id=str(admin_account.id),
                request_id=request_id,
                route=route,
                method=method,
                status_code=401,
                metadata={"reason": "inactive_admin"},
            )
            raise AuthenticationError("admin account is inactive")

        admin_account.last_login_at = self.now_provider()
        raw_refresh_token = generate_refresh_token()
        refresh_token = AdminRefreshToken(
            admin_account_id=admin_account.id,
            token_hash=hash_token(raw_refresh_token),
            issued_at=self.now_provider(),
            expires_at=self.now_provider()
            + timedelta(days=self.settings.auth_refresh_token_ttl_days),
            created_ip=created_ip,
            user_agent=user_agent,
        )
        self.refresh_token_repository.add(refresh_token)
        commit_session(self.session)

        issued = IssuedAdminTokens(
            access_token=self._issue_access_token(admin_account),
            refresh_token=raw_refresh_token,
            expires_in_seconds=self.settings.auth_access_token_ttl_minutes * 60,
            admin_account=self.admin_repository.get(admin_account.id) or admin_account,
        )
        self.audit_service.safe_record(
            actor=self._actor_from_admin(admin_account),
            action="auth.login_success",
            resource_type="admin_account",
            resource_id=str(admin_account.id),
            request_id=request_id,
            route=route,
            method=method,
            status_code=200,
            metadata={"refresh_token_id": str(refresh_token.id)},
        )
        return issued

    def refresh(
        self,
        *,
        refresh_token: str,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
    ) -> IssuedAdminTokens:
        stored = self._require_active_refresh_token(refresh_token)
        admin_account = stored.admin_account
        if not admin_account.is_active:
            raise AuthenticationError("admin account is inactive")

        now = self.now_provider()
        stored.revoked_at = now
        stored.last_used_at = now

        new_raw_refresh_token = generate_refresh_token()
        new_refresh_token = AdminRefreshToken(
            admin_account_id=admin_account.id,
            token_hash=hash_token(new_raw_refresh_token),
            issued_at=now,
            expires_at=now + timedelta(days=self.settings.auth_refresh_token_ttl_days),
            created_ip=stored.created_ip,
            user_agent=stored.user_agent,
        )
        self.refresh_token_repository.add(new_refresh_token)
        commit_session(self.session)

        self.audit_service.safe_record(
            actor=self._actor_from_admin(admin_account),
            action="auth.refresh",
            resource_type="admin_account",
            resource_id=str(admin_account.id),
            request_id=request_id,
            route=route,
            method=method,
            status_code=200,
            metadata={"refresh_token_id": str(new_refresh_token.id)},
        )

        return IssuedAdminTokens(
            access_token=self._issue_access_token(admin_account),
            refresh_token=new_raw_refresh_token,
            expires_in_seconds=self.settings.auth_access_token_ttl_minutes * 60,
            admin_account=self.admin_repository.get(admin_account.id) or admin_account,
        )

    def logout(
        self,
        *,
        actor: ActorContext,
        refresh_token: str,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
    ) -> str:
        if not actor.is_admin or actor.actor_id is None:
            raise AuthenticationError("admin authentication is required")
        stored = self.refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        if stored is None or stored.admin_account_id != actor.actor_id:
            raise AuthenticationError("refresh token was not found")
        if stored.revoked_at is None:
            stored.revoked_at = self.now_provider()
            stored.last_used_at = self.now_provider()
            commit_session(self.session)
        self.audit_service.safe_record(
            actor=actor,
            action="auth.logout",
            resource_type="admin_account",
            resource_id=str(actor.actor_id),
            request_id=request_id,
            route=route,
            method=method,
            status_code=200,
            metadata={"refresh_token_id": str(stored.id)},
        )
        return "revoked"

    def authenticate_access_token(self, token: str) -> ActorContext:
        payload = decode_hs256_jwt(
            token,
            secret=self.settings.auth_jwt_secret,
            issuer=self.settings.auth_jwt_issuer,
            audience=self.settings.auth_jwt_audience,
            expected_type="access",
            now=self.now_provider(),
        )
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise AuthenticationError("token subject is missing")
        try:
            admin_account_id = UUID(subject)
        except ValueError as exc:
            raise AuthenticationError("token subject is invalid") from exc

        admin_account = self.admin_repository.get(admin_account_id)
        if admin_account is None:
            raise AuthenticationError("admin account was not found")
        if not admin_account.is_active:
            raise AuthenticationError("admin account is inactive")
        return self._actor_from_admin(admin_account)

    def authenticate_internal_service_token(self, token: str) -> ActorContext | None:
        if not token or not hmac.compare_digest(token, self.settings.internal_service_token):
            return None
        return ActorContext(
            actor_type=AuditActorType.SERVICE,
            actor_label="internal-service",
            is_active=True,
        )

    def _require_active_refresh_token(self, refresh_token: str) -> AdminRefreshToken:
        stored = self.refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        if stored is None:
            raise AuthenticationError("refresh token was not found")
        if stored.revoked_at is not None:
            raise AuthenticationError("refresh token has been revoked")
        if _coerce_utc(stored.expires_at) <= _coerce_utc(self.now_provider()):
            raise AuthenticationError("refresh token has expired")
        return stored

    def _issue_access_token(self, admin_account: AdminAccount) -> str:
        now = self.now_provider()
        access_expires_at = now + timedelta(minutes=self.settings.auth_access_token_ttl_minutes)
        return encode_hs256_jwt(
            {
                "sub": str(admin_account.id),
                "email": admin_account.email,
                "role": admin_account.role.value,
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int(access_expires_at.timestamp()),
                "iss": self.settings.auth_jwt_issuer,
                "aud": self.settings.auth_jwt_audience,
            },
            self.settings.auth_jwt_secret,
        )

    def _actor_from_admin(self, admin_account: AdminAccount) -> ActorContext:
        return ActorContext(
            actor_type=AuditActorType.ADMIN,
            actor_id=admin_account.id,
            actor_label=admin_account.email,
            admin_role=admin_account.role,
            is_active=admin_account.is_active,
        )


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
