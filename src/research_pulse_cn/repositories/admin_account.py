"""Admin account repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import AdminAccount
from research_pulse_cn.domain.enums import AdminRole


class AdminAccountRepository:
    """Persistence operations for admin identities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[AdminAccount]:
        statement = select(AdminAccount).order_by(AdminAccount.created_at.asc())
        return list(self.session.scalars(statement))

    def get(self, admin_account_id: UUID) -> AdminAccount | None:
        statement = (
            select(AdminAccount)
            .options(selectinload(AdminAccount.refresh_tokens))
            .where(AdminAccount.id == admin_account_id)
        )
        return self.session.scalar(statement)

    def get_by_email(self, email: str) -> AdminAccount | None:
        statement = (
            select(AdminAccount)
            .options(selectinload(AdminAccount.refresh_tokens))
            .where(func.lower(AdminAccount.email) == email.lower())
        )
        return self.session.scalar(statement)

    def add(self, account: AdminAccount) -> AdminAccount:
        self.session.add(account)
        self.session.flush()
        self.session.refresh(account)
        return account

    def count_active_super_admins(self) -> int:
        statement = (
            select(func.count())
            .select_from(AdminAccount)
            .where(
                AdminAccount.role == AdminRole.SUPER_ADMIN,
                AdminAccount.is_active.is_(True),
            )
        )
        return int(self.session.scalar(statement) or 0)

    def has_no_other_active_super_admin(self, admin_account_id: UUID) -> bool:
        statement = (
            select(func.count())
            .select_from(AdminAccount)
            .where(
                AdminAccount.role == AdminRole.SUPER_ADMIN,
                AdminAccount.is_active.is_(True),
                AdminAccount.id != admin_account_id,
            )
        )
        return int(self.session.scalar(statement) or 0) == 0

    def list_recently_logged_in(self, since: datetime) -> list[AdminAccount]:
        statement = select(AdminAccount).where(AdminAccount.last_login_at >= since)
        return list(self.session.scalars(statement))
