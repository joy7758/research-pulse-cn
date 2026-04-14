"""SQLAlchemy ORM models for the Research Pulse CN domain."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from research_pulse_cn.db.base import Base
from research_pulse_cn.db.types import JSON_VARIANT
from research_pulse_cn.domain.enums import (
    AdminRole,
    AuditActorType,
    ChannelType,
    DeliveryAttemptStatus,
    DeliveryJobStatus,
    PaperType,
    PulseCardType,
    PulseJobScheduledReason,
    PulseJobStatus,
    SignalSource,
    SubscriptionFrequency,
    WorkerRole,
    WorkerStatus,
)


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class TimestampMixin:
    """Common created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AdminAccount(TimestampMixin, Base):
    __tablename__ = "admin_accounts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, native_enum=False),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    refresh_tokens: Mapped[list[AdminRefreshToken]] = relationship(
        back_populates="admin_account",
        cascade="all, delete-orphan",
    )


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    field: Mapped[str | None] = mapped_column(String(255))
    interests: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    watched_topics: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    watched_venues: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    reminder_preferences: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    risk_thresholds: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)

    papers: Mapped[list[PaperProfile]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription_policies: Mapped[list[SubscriptionPolicy]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pulse_jobs: Mapped[list[PulseJob]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pulse_cards: Mapped[list[PulseCard]] = relationship(back_populates="user")
    delivery_jobs: Mapped[list[DeliveryJob]] = relationship(back_populates="user")


class PaperProfile(TimestampMixin, Base):
    __tablename__ = "paper_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_zh: Mapped[str | None] = mapped_column(String(500))
    title_en: Mapped[str | None] = mapped_column(String(500))
    type: Mapped[PaperType] = mapped_column(Enum(PaperType, native_enum=False), nullable=False)
    stage: Mapped[str] = mapped_column(String(255), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(255))
    identifiers: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    source_links: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    last_touch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_action: Mapped[str | None] = mapped_column(String(500))
    blocker: Mapped[str | None] = mapped_column(String(500))
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    user: Mapped[UserProfile] = relationship(back_populates="papers")
    progress_events: Mapped[list[ProgressEvent]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    signal_snapshots: Mapped[list[SignalSnapshot]] = relationship(
        back_populates="paper", cascade="all, delete-orphan", order_by="SignalSnapshot.fetched_at"
    )
    sourced_pulse_cards: Mapped[list[PulseCard]] = relationship(
        back_populates="source_paper",
        foreign_keys="PulseCard.source_paper_id",
    )


class ProgressEvent(Base):
    __tablename__ = "progress_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(ForeignKey("paper_profiles.id", ondelete="CASCADE"))
    stage: Mapped[str] = mapped_column(String(255), nullable=False)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_links: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    owner: Mapped[str | None] = mapped_column(String(255))

    paper: Mapped[PaperProfile] = relationship(back_populates="progress_events")


class SignalSnapshot(Base):
    __tablename__ = "signal_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(ForeignKey("paper_profiles.id", ondelete="CASCADE"))
    source: Mapped[SignalSource] = mapped_column(
        Enum(SignalSource, native_enum=False), nullable=False
    )
    citation_count: Mapped[int | None] = mapped_column(Integer)
    download_count: Mapped[int | None] = mapped_column(Integer)
    read_count: Mapped[int | None] = mapped_column(Integer)
    inclusion_status: Mapped[str | None] = mapped_column(String(255))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped[PaperProfile] = relationship(back_populates="signal_snapshots")


class SubscriptionPolicy(TimestampMixin, Base):
    __tablename__ = "subscription_policies"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    frequency: Mapped[SubscriptionFrequency] = mapped_column(
        Enum(SubscriptionFrequency, native_enum=False), nullable=False
    )
    quiet_hours: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    frequency_cap: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    endpoint: Mapped[str | None] = mapped_column(String(500))
    policy: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)

    user: Mapped[UserProfile] = relationship(back_populates="subscription_policies")
    pulse_jobs: Mapped[list[PulseJob]] = relationship(back_populates="subscription_policy")


class PulseJob(TimestampMixin, Base):
    __tablename__ = "pulse_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    subscription_policy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscription_policies.id", ondelete="SET NULL")
    )
    source_pulse_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pulse_jobs.id", ondelete="SET NULL")
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    scheduled_reason: Mapped[PulseJobScheduledReason] = mapped_column(
        Enum(PulseJobScheduledReason, native_enum=False),
        default=PulseJobScheduledReason.MANUAL_RUN,
        nullable=False,
    )
    schedule_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[PulseJobStatus] = mapped_column(
        Enum(PulseJobStatus, native_enum=False),
        default=PulseJobStatus.PENDING,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(255))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    user: Mapped[UserProfile] = relationship(back_populates="pulse_jobs")
    subscription_policy: Mapped[SubscriptionPolicy | None] = relationship(
        back_populates="pulse_jobs"
    )
    source_pulse_job: Mapped[PulseJob | None] = relationship(
        remote_side=[id],
        back_populates="replay_jobs",
        foreign_keys=[source_pulse_job_id],
    )
    replay_jobs: Mapped[list[PulseJob]] = relationship(
        back_populates="source_pulse_job",
        foreign_keys=[source_pulse_job_id],
    )
    cards: Mapped[list[PulseCard]] = relationship(
        back_populates="pulse_job", cascade="all, delete-orphan"
    )
    delivery_jobs: Mapped[list[DeliveryJob]] = relationship(back_populates="pulse_job")


class PulseCard(Base):
    __tablename__ = "pulse_cards"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    pulse_job_id: Mapped[UUID] = mapped_column(ForeignKey("pulse_jobs.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_paper_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_profiles.id", ondelete="SET NULL")
    )
    card_type: Mapped[PulseCardType] = mapped_column(
        Enum(PulseCardType, native_enum=False), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    score_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    why_now: Mapped[str] = mapped_column(Text, nullable=False)
    action_text: Mapped[str | None] = mapped_column(String(500))
    deep_link: Mapped[str | None] = mapped_column(String(500))
    evidence_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    candidate_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    generated_by: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pulse_job: Mapped[PulseJob] = relationship(back_populates="cards")
    user: Mapped[UserProfile] = relationship(back_populates="pulse_cards")
    source_paper: Mapped[PaperProfile | None] = relationship(
        back_populates="sourced_pulse_cards",
        foreign_keys=[source_paper_id],
    )
    delivery_jobs: Mapped[list[DeliveryJob]] = relationship(back_populates="pulse_card")


class DeliveryJob(TimestampMixin, Base):
    __tablename__ = "delivery_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    pulse_card_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pulse_cards.id", ondelete="SET NULL")
    )
    pulse_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pulse_jobs.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    idem_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    status: Mapped[DeliveryJobStatus] = mapped_column(
        Enum(DeliveryJobStatus, native_enum=False),
        default=DeliveryJobStatus.PENDING,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    pulse_card: Mapped[PulseCard | None] = relationship(back_populates="delivery_jobs")
    pulse_job: Mapped[PulseJob | None] = relationship(back_populates="delivery_jobs")
    user: Mapped[UserProfile] = relationship(back_populates="delivery_jobs")
    attempts: Mapped[list[DeliveryAttempt]] = relationship(
        back_populates="delivery_job",
        cascade="all, delete-orphan",
        order_by="DeliveryAttempt.attempt_number",
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    worker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    worker_role: Mapped[WorkerRole] = mapped_column(
        Enum(WorkerRole, native_enum=False), nullable=False
    )
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, native_enum=False), nullable=False
    )
    hostname_or_instance: Mapped[str] = mapped_column(String(255), nullable=False)
    pid: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_VARIANT, default=dict)


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    delivery_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("delivery_jobs.id", ondelete="CASCADE")
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False), nullable=False
    )
    adapter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DeliveryAttemptStatus] = mapped_column(
        Enum(DeliveryAttemptStatus, native_enum=False), nullable=False
    )
    response_summary: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    delivery_job: Mapped[DeliveryJob] = relationship(back_populates="attempts")


class AdminRefreshToken(Base):
    __tablename__ = "admin_refresh_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    admin_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("admin_accounts.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_ip: Mapped[str | None] = mapped_column(String(255))
    user_agent: Mapped[str | None] = mapped_column(String(500))

    admin_account: Mapped[AdminAccount] = relationship(back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_type: Mapped[AuditActorType] = mapped_column(
        Enum(AuditActorType, native_enum=False),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(Uuid)
    actor_label: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(255))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[str | None] = mapped_column(String(255))
    route: Mapped[str | None] = mapped_column(String(255))
    method: Mapped[str | None] = mapped_column(String(20))
    status_code: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON_VARIANT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
