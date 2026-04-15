"""Admin account management service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import hash_password
from research_pulse_cn.core.errors import ConflictError, NotFoundError
from research_pulse_cn.db.models import AdminAccount
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.repositories.admin_account import AdminAccountRepository
from research_pulse_cn.repositories.audit_log import AuditLogRepository
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.common import commit_session


class AdminService:
    """Manage admin identities without leaking into business user models."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AdminAccountRepository(session)
        self.audit_service = AuditService(session)
        self.audit_repository = AuditLogRepository(session)

    def list_accounts(self) -> list[AdminAccount]:
        return self.repository.list()

    def get_account(self, admin_account_id):
        account = self.repository.get(admin_account_id)
        if account is None:
            raise NotFoundError(f"admin account {admin_account_id} was not found")
        return account

    def get_by_email(self, email: str) -> AdminAccount | None:
        return self.repository.get_by_email(email)

    def create_account(
        self,
        *,
        email: str,
        password: str,
        role: AdminRole,
        display_name: str | None,
        is_active: bool,
        must_change_password: bool,
        actor: ActorContext | None = None,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
        audit_metadata: dict | None = None,
    ) -> AdminAccount:
        if self.repository.get_by_email(email) is not None:
            raise ConflictError(f"admin account with email {email} already exists")

        account = AdminAccount(
            email=email.lower(),
            password_hash=hash_password(password),
            role=role,
            display_name=display_name,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        self.repository.add(account)
        commit_session(self.session)
        self.audit_service.safe_record(
            actor=actor,
            action="admin_account.create",
            resource_type="admin_account",
            resource_id=str(account.id),
            request_id=request_id,
            route=route,
            method=method,
            status_code=201,
            metadata={
                "email": account.email,
                "role": account.role.value,
                **dict(audit_metadata or {}),
            },
        )
        return self.get_account(account.id)

    def update_account(
        self,
        admin_account_id,
        *,
        role: AdminRole | None = None,
        display_name: str | None = None,
        is_active: bool | None = None,
        must_change_password: bool | None = None,
        actor: ActorContext | None = None,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
        audit_metadata: dict | None = None,
    ) -> AdminAccount:
        account = self.get_account(admin_account_id)
        target_role = role or account.role
        target_is_active = account.is_active if is_active is None else is_active
        self._ensure_super_admin_guard(
            account=account,
            target_role=target_role,
            target_is_active=target_is_active,
        )

        if role is not None:
            account.role = role
        if display_name is not None:
            account.display_name = display_name
        if is_active is not None:
            account.is_active = is_active
        if must_change_password is not None:
            account.must_change_password = must_change_password
        commit_session(self.session)
        self.audit_service.safe_record(
            actor=actor,
            action="admin_account.update",
            resource_type="admin_account",
            resource_id=str(account.id),
            request_id=request_id,
            route=route,
            method=method,
            status_code=200,
            metadata={
                "role": account.role.value,
                "is_active": account.is_active,
                "must_change_password": account.must_change_password,
                **dict(audit_metadata or {}),
            },
        )
        return self.get_account(account.id)

    def set_password(
        self,
        admin_account_id,
        *,
        password: str,
        must_change_password: bool,
        actor: ActorContext | None = None,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
        audit_metadata: dict | None = None,
    ) -> AdminAccount:
        account = self.get_account(admin_account_id)
        account.password_hash = hash_password(password)
        account.must_change_password = must_change_password
        commit_session(self.session)
        self.audit_service.safe_record(
            actor=actor,
            action="admin_account.set_password",
            resource_type="admin_account",
            resource_id=str(account.id),
            request_id=request_id,
            route=route,
            method=method,
            status_code=200,
            metadata={"must_change_password": must_change_password, **dict(audit_metadata or {})},
        )
        return self.get_account(account.id)

    def bootstrap_super_admin(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None = None,
    ) -> AdminAccount:
        existing = self.repository.get_by_email(email)
        if existing is None:
            account = AdminAccount(
                email=email.lower(),
                password_hash=hash_password(password),
                role=AdminRole.SUPER_ADMIN,
                display_name=display_name,
                is_active=True,
                must_change_password=False,
            )
            self.repository.add(account)
        else:
            existing.password_hash = hash_password(password)
            existing.role = AdminRole.SUPER_ADMIN
            existing.display_name = display_name or existing.display_name
            existing.is_active = True
            existing.must_change_password = False
            account = existing
        commit_session(self.session)
        return self.get_account(account.id)

    def list_audit_logs(self, *, actor_type=None, action=None, since=None, limit: int = 100):
        return self.audit_repository.list(
            actor_type=actor_type,
            action=action,
            since=since,
            limit=limit,
        )

    def _ensure_super_admin_guard(
        self,
        *,
        account: AdminAccount,
        target_role: AdminRole,
        target_is_active: bool,
    ) -> None:
        is_demoting_super_admin = (
            account.role == AdminRole.SUPER_ADMIN
            and account.is_active
            and (target_role != AdminRole.SUPER_ADMIN or not target_is_active)
        )
        if is_demoting_super_admin and self.repository.has_no_other_active_super_admin(account.id):
            raise ConflictError("cannot remove or deactivate the last active super_admin")
