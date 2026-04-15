"""API dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from research_pulse_cn.db.session import get_db_session
from research_pulse_cn.services.admin import AdminService
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.auth import AuthService
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.digest import DigestService
from research_pulse_cn.services.external_retrieval import ExternalRetrievalService
from research_pulse_cn.services.mini import MiniService
from research_pulse_cn.services.ops import OpsService
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.pulse import PulseService
from research_pulse_cn.services.research_watch import ResearchWatchProfileService
from research_pulse_cn.services.scheduler import SchedulerService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService
from research_pulse_cn.services.subscription_self_service import (
    SubscriptionSelfServiceService,
)
from research_pulse_cn.services.sync import SyncService
from research_pulse_cn.services.user import UserService
from research_pulse_cn.services.work_activity import WorkActivityService


def get_session() -> Iterator[Session]:
    yield from get_db_session()


SessionDep = Annotated[Session, Depends(get_session)]


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


def get_paper_service(session: SessionDep) -> PaperService:
    return PaperService(session)


def get_subscription_policy_service(session: SessionDep) -> SubscriptionPolicyService:
    return SubscriptionPolicyService(session)


def get_pulse_service(session: SessionDep) -> PulseService:
    return PulseService(session)


def get_work_activity_service(session: SessionDep) -> WorkActivityService:
    return WorkActivityService(session)


def get_research_watch_profile_service(session: SessionDep) -> ResearchWatchProfileService:
    return ResearchWatchProfileService(session)


def get_external_retrieval_service(session: SessionDep) -> ExternalRetrievalService:
    return ExternalRetrievalService(session)


def get_delivery_service(session: SessionDep) -> DeliveryService:
    return DeliveryService(session)


def get_digest_service(session: SessionDep) -> DigestService:
    return DigestService(session)


def get_mini_service(session: SessionDep) -> MiniService:
    return MiniService(session)


def get_subscription_self_service_service(
    session: SessionDep,
) -> SubscriptionSelfServiceService:
    return SubscriptionSelfServiceService(session)


def get_scheduler_service(session: SessionDep) -> SchedulerService:
    return SchedulerService(session)


def get_ops_service(session: SessionDep) -> OpsService:
    return OpsService(session)


def get_admin_service(session: SessionDep) -> AdminService:
    return AdminService(session)


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


def get_audit_service(session: SessionDep) -> AuditService:
    return AuditService(session)


def get_sync_service(session: SessionDep) -> SyncService:
    return SyncService(session)
