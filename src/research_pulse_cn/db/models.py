"""SQLAlchemy ORM models for the Research Pulse CN domain."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from research_pulse_cn.db.base import Base
from research_pulse_cn.db.types import JSON_VARIANT
from research_pulse_cn.domain.enums import (
    AdminRole,
    AuditActorType,
    ChannelType,
    ClientType,
    DeliveryAttemptStatus,
    DeliveryJobStatus,
    DigestDeliveryDecisionStatus,
    DigestDispatchMode,
    DigestDispatchRunStatus,
    DigestPublicationAttemptStatus,
    DigestPublicationMode,
    DigestPublicationStatus,
    DigestPublicationTarget,
    ExternalRetrievalPlanStatus,
    ExternalRetrievalRunStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
    MiniReadGrantStatus,
    MiniReadGrantType,
    OfficialAccountBindingHandshakeSessionStatus,
    OfficialAccountCallbackPayloadFormat,
    OfficialAccountCallbackProcessingStatus,
    OfficialAccountProviderMode,
    PaperType,
    PulseCardType,
    PulseDigestIssueStatus,
    PulseJobScheduledReason,
    PulseJobStatus,
    ResearchWatchProfileSourceMode,
    SignalSource,
    SubscriptionFrequency,
    SubscriptionSelfServiceGrantStatus,
    SyncEventSource,
    SyncEventType,
    SyncMutationStatus,
    WeChatBindingChannelType,
    WeChatBindingState,
    WorkActivitySource,
    WorkActivityType,
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
    created_mini_read_grants: Mapped[list[MiniReadGrant]] = relationship(
        back_populates="created_by_admin",
    )
    issued_subscription_self_service_grants: Mapped[list[SubscriptionSelfServiceGrant]] = (
        relationship(
            back_populates="issued_by_admin",
        )
    )
    issued_official_account_binding_handshake_sessions: Mapped[
        list[OfficialAccountBindingHandshakeSession]
    ] = relationship(
        back_populates="issued_by_admin",
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
    client_devices: Mapped[list[ClientDevice]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    wechat_identity_bindings: Mapped[list[WeChatIdentityBinding]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    digest_issues: Mapped[list[PulseDigestIssue]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="PulseDigestIssue.issue_date",
    )
    mini_read_grants: Mapped[list[MiniReadGrant]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscription_self_service_grants: Mapped[list[SubscriptionSelfServiceGrant]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    official_account_binding_handshake_sessions: Mapped[
        list[OfficialAccountBindingHandshakeSession]
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="OfficialAccountBindingHandshakeSession.created_at.desc()",
    )
    work_activity_events: Mapped[list[WorkActivityEvent]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="WorkActivityEvent.happened_at.desc()",
    )
    research_watch_profiles: Mapped[list[ResearchWatchProfile]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ResearchWatchProfile.updated_at.desc()",
    )
    external_retrieval_plans: Mapped[list[ExternalRetrievalPlan]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ExternalRetrievalPlan.updated_at.desc()",
    )
    external_retrieval_runs: Mapped[list[ExternalRetrievalRun]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ExternalRetrievalRun.created_at.desc()",
    )
    digest_dispatch_runs: Mapped[list[DigestDispatchRun]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="DigestDispatchRun.created_at.desc()",
    )
    digest_delivery_decisions: Mapped[list[DigestDeliveryDecision]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="DigestDeliveryDecision.created_at.desc()",
    )
    external_retrieval_results: Mapped[list[ExternalRetrievedRecord]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ExternalRetrievedRecord.created_at.desc()",
    )
    sync_events: Mapped[list[SyncEvent]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="SyncEvent.sequence",
    )


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
    work_activity_events: Mapped[list[WorkActivityEvent]] = relationship(
        back_populates="paper",
    )
    research_watch_profiles: Mapped[list[ResearchWatchProfile]] = relationship(
        back_populates="paper",
    )
    external_retrieval_plans: Mapped[list[ExternalRetrievalPlan]] = relationship(
        back_populates="paper",
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
    digest_issues: Mapped[list[PulseDigestIssue]] = relationship(
        back_populates="source_pulse_job",
        foreign_keys="PulseDigestIssue.source_pulse_job_id",
    )


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
    external_reference_key: Mapped[str | None] = mapped_column(String(500))
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
    digest_items: Mapped[list[PulseDigestItem]] = relationship(
        back_populates="pulse_card",
        cascade="all, delete-orphan",
        order_by="PulseDigestItem.sort_order",
    )


class WeChatIdentityBinding(TimestampMixin, Base):
    __tablename__ = "wechat_identity_bindings"
    __table_args__ = (
        UniqueConstraint(
            "channel_type",
            "app_id",
            "openid",
            name="uq_wechat_identity_bindings_channel_app_openid",
        ),
        Index("ix_wechat_identity_bindings_unionid", "unionid"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    channel_type: Mapped[WeChatBindingChannelType] = mapped_column(
        Enum(WeChatBindingChannelType, native_enum=False),
        nullable=False,
    )
    app_id: Mapped[str] = mapped_column(String(255), nullable=False)
    openid: Mapped[str] = mapped_column(String(255), nullable=False)
    unionid: Mapped[str | None] = mapped_column(String(255))
    bind_state: Mapped[WeChatBindingState] = mapped_column(
        Enum(WeChatBindingState, native_enum=False),
        nullable=False,
        default=WeChatBindingState.PENDING,
    )
    subscribed: Mapped[bool] = mapped_column(default=False, nullable=False)
    digest_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    display_label: Mapped[str | None] = mapped_column(String(255))
    subscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON_VARIANT)

    user: Mapped[UserProfile] = relationship(back_populates="wechat_identity_bindings")
    publication_jobs: Mapped[list[DigestPublicationJob]] = relationship(
        back_populates="binding",
        cascade="all, delete-orphan",
    )
    callback_events: Mapped[list[OfficialAccountCallbackEvent]] = relationship(
        back_populates="linked_binding",
    )
    mini_read_grants: Mapped[list[MiniReadGrant]] = relationship(
        back_populates="binding",
    )
    subscription_self_service_grants: Mapped[list[SubscriptionSelfServiceGrant]] = relationship(
        back_populates="binding",
    )
    claimed_official_account_binding_handshake_sessions: Mapped[
        list[OfficialAccountBindingHandshakeSession]
    ] = relationship(
        back_populates="claimed_binding",
    )


class PulseDigestIssue(TimestampMixin, Base):
    __tablename__ = "pulse_digest_issues"
    __table_args__ = (
        UniqueConstraint("user_id", "issue_date", name="uq_pulse_digest_issues_user_issue_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_pulse_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pulse_jobs.id", ondelete="SET NULL")
    )
    status: Mapped[PulseDigestIssueStatus] = mapped_column(
        Enum(PulseDigestIssueStatus, native_enum=False),
        nullable=False,
        default=PulseDigestIssueStatus.DRAFT,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    highlight_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_card_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deep_link_path: Mapped[str | None] = mapped_column(String(500))
    content_payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    build_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserProfile] = relationship(back_populates="digest_issues")
    source_pulse_job: Mapped[PulseJob | None] = relationship(
        back_populates="digest_issues",
        foreign_keys=[source_pulse_job_id],
    )
    items: Mapped[list[PulseDigestItem]] = relationship(
        back_populates="digest_issue",
        cascade="all, delete-orphan",
        order_by="PulseDigestItem.sort_order",
    )
    publication_jobs: Mapped[list[DigestPublicationJob]] = relationship(
        back_populates="digest_issue",
        cascade="all, delete-orphan",
    )
    dispatch_runs: Mapped[list[DigestDispatchRun]] = relationship(
        back_populates="digest_issue",
        cascade="all, delete-orphan",
        order_by="DigestDispatchRun.created_at.desc()",
    )
    delivery_decisions: Mapped[list[DigestDeliveryDecision]] = relationship(
        back_populates="digest_issue",
        cascade="all, delete-orphan",
        order_by="DigestDeliveryDecision.created_at.desc()",
    )
    mini_read_grants: Mapped[list[MiniReadGrant]] = relationship(
        back_populates="digest_issue",
    )


class MiniReadGrant(TimestampMixin, Base):
    __tablename__ = "mini_read_grants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    binding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wechat_identity_bindings.id", ondelete="SET NULL")
    )
    digest_issue_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pulse_digest_issues.id", ondelete="SET NULL")
    )
    grant_type: Mapped[MiniReadGrantType] = mapped_column(
        Enum(MiniReadGrantType, native_enum=False),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[MiniReadGrantStatus] = mapped_column(
        Enum(MiniReadGrantStatus, native_enum=False),
        nullable=False,
        default=MiniReadGrantStatus.ACTIVE,
    )
    scope_json: Mapped[dict[str, Any] | None] = mapped_column("scope", JSON_VARIANT)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_accounts.id", ondelete="SET NULL")
    )

    user: Mapped[UserProfile] = relationship(back_populates="mini_read_grants")
    binding: Mapped[WeChatIdentityBinding | None] = relationship(back_populates="mini_read_grants")
    digest_issue: Mapped[PulseDigestIssue | None] = relationship(back_populates="mini_read_grants")
    created_by_admin: Mapped[AdminAccount | None] = relationship(
        back_populates="created_mini_read_grants"
    )


class SubscriptionSelfServiceGrant(TimestampMixin, Base):
    __tablename__ = "subscription_self_service_grants"
    __table_args__ = (
        Index(
            "ix_subscription_self_service_grants_user_channel_created_at",
            "user_id",
            "channel",
            "created_at",
        ),
        Index(
            "ix_subscription_self_service_grants_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    binding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wechat_identity_bindings.id", ondelete="SET NULL")
    )
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False),
        nullable=False,
    )
    grant_scope_json: Mapped[dict[str, Any] | None] = mapped_column("grant_scope", JSON_VARIANT)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[SubscriptionSelfServiceGrantStatus] = mapped_column(
        Enum(SubscriptionSelfServiceGrantStatus, native_enum=False),
        nullable=False,
        default=SubscriptionSelfServiceGrantStatus.ACTIVE,
    )
    display_label: Mapped[str | None] = mapped_column(String(255))
    issued_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_accounts.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserProfile] = relationship(back_populates="subscription_self_service_grants")
    binding: Mapped[WeChatIdentityBinding | None] = relationship(
        back_populates="subscription_self_service_grants"
    )
    issued_by_admin: Mapped[AdminAccount | None] = relationship(
        back_populates="issued_subscription_self_service_grants"
    )
    official_account_binding_handshake_sessions: Mapped[
        list[OfficialAccountBindingHandshakeSession]
    ] = relationship(back_populates="self_service_grant")


class OfficialAccountBindingHandshakeSession(TimestampMixin, Base):
    __tablename__ = "official_account_binding_handshake_sessions"
    __table_args__ = (
        Index(
            "ix_oa_binding_handshake_sessions_user_channel_created_at",
            "user_id",
            "channel",
            "created_at",
        ),
        Index(
            "ix_oa_binding_handshake_sessions_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False),
        nullable=False,
    )
    app_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_label: Mapped[str | None] = mapped_column(String(255))
    self_service_grant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscription_self_service_grants.id", ondelete="SET NULL")
    )
    issued_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_accounts.id", ondelete="SET NULL")
    )
    state_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[OfficialAccountBindingHandshakeSessionStatus] = mapped_column(
        Enum(OfficialAccountBindingHandshakeSessionStatus, native_enum=False),
        nullable=False,
        default=OfficialAccountBindingHandshakeSessionStatus.PENDING,
    )
    matched_callback_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("official_account_callback_events.id", ondelete="SET NULL")
    )
    claimed_binding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wechat_identity_bindings.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserProfile] = relationship(
        back_populates="official_account_binding_handshake_sessions"
    )
    self_service_grant: Mapped[SubscriptionSelfServiceGrant | None] = relationship(
        back_populates="official_account_binding_handshake_sessions"
    )
    issued_by_admin: Mapped[AdminAccount | None] = relationship(
        back_populates="issued_official_account_binding_handshake_sessions"
    )
    matched_callback_event: Mapped[OfficialAccountCallbackEvent | None] = relationship(
        back_populates="matched_handshake_sessions",
        foreign_keys=[matched_callback_event_id],
    )
    claimed_binding: Mapped[WeChatIdentityBinding | None] = relationship(
        back_populates="claimed_official_account_binding_handshake_sessions"
    )


class PulseDigestItem(Base):
    __tablename__ = "pulse_digest_items"
    __table_args__ = (
        UniqueConstraint(
            "digest_issue_id",
            "pulse_card_id",
            name="uq_pulse_digest_items_issue_card",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    digest_issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("pulse_digest_issues.id", ondelete="CASCADE")
    )
    pulse_card_id: Mapped[UUID] = mapped_column(ForeignKey("pulse_cards.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    card_type: Mapped[PulseCardType] = mapped_column(
        Enum(PulseCardType, native_enum=False),
        nullable=False,
    )
    source_paper_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_profiles.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    why_now: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    digest_issue: Mapped[PulseDigestIssue] = relationship(back_populates="items")
    pulse_card: Mapped[PulseCard] = relationship(back_populates="digest_items")
    source_paper: Mapped[PaperProfile | None] = relationship(foreign_keys=[source_paper_id])


class DigestPublicationJob(TimestampMixin, Base):
    __tablename__ = "digest_publication_jobs"
    __table_args__ = (
        UniqueConstraint(
            "digest_issue_id",
            "binding_id",
            "publish_target",
            name="uq_digest_publication_jobs_issue_binding_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    digest_issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("pulse_digest_issues.id", ondelete="CASCADE")
    )
    binding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wechat_identity_bindings.id", ondelete="SET NULL")
    )
    publish_target: Mapped[DigestPublicationTarget] = mapped_column(
        Enum(DigestPublicationTarget, native_enum=False),
        nullable=False,
    )
    status: Mapped[DigestPublicationStatus] = mapped_column(
        Enum(DigestPublicationStatus, native_enum=False),
        nullable=False,
        default=DigestPublicationStatus.PENDING,
    )
    publish_mode: Mapped[DigestPublicationMode] = mapped_column(
        Enum(DigestPublicationMode, native_enum=False),
        nullable=False,
        default=DigestPublicationMode.MANUAL_PREVIEW,
    )
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False, default="stub")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(Text)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    digest_issue: Mapped[PulseDigestIssue] = relationship(back_populates="publication_jobs")
    binding: Mapped[WeChatIdentityBinding | None] = relationship(back_populates="publication_jobs")
    attempts: Mapped[list[DigestPublicationAttempt]] = relationship(
        back_populates="digest_publication_job",
        cascade="all, delete-orphan",
        order_by="DigestPublicationAttempt.attempt_number",
    )


class DigestDispatchRun(TimestampMixin, Base):
    __tablename__ = "digest_dispatch_runs"
    __table_args__ = (
        Index(
            "ix_digest_dispatch_runs_issue_target_status",
            "digest_issue_id",
            "publish_target",
            "status",
        ),
        Index("ix_digest_dispatch_runs_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    digest_issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("pulse_digest_issues.id", ondelete="CASCADE")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    publish_target: Mapped[DigestPublicationTarget] = mapped_column(
        Enum(DigestPublicationTarget, native_enum=False),
        nullable=False,
    )
    dispatch_mode: Mapped[DigestDispatchMode] = mapped_column(
        Enum(DigestDispatchMode, native_enum=False),
        nullable=False,
        default=DigestDispatchMode.MANUAL,
    )
    provider_mode: Mapped[OfficialAccountProviderMode] = mapped_column(
        Enum(OfficialAccountProviderMode, native_enum=False),
        nullable=False,
    )
    status: Mapped[DigestDispatchRunStatus] = mapped_column(
        Enum(DigestDispatchRunStatus, native_enum=False),
        nullable=False,
        default=DigestDispatchRunStatus.PENDING,
    )
    total_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    previewed_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    digest_issue: Mapped[PulseDigestIssue] = relationship(back_populates="dispatch_runs")
    user: Mapped[UserProfile] = relationship(back_populates="digest_dispatch_runs")
    attempts: Mapped[list[DigestPublicationAttempt]] = relationship(
        back_populates="dispatch_run",
        order_by="DigestPublicationAttempt.started_at",
    )
    delivery_decisions: Mapped[list[DigestDeliveryDecision]] = relationship(
        back_populates="dispatch_run",
        order_by="DigestDeliveryDecision.created_at",
    )


class DigestDeliveryDecision(Base):
    __tablename__ = "digest_delivery_decisions"
    __table_args__ = (
        Index(
            "ix_digest_delivery_decisions_issue_channel_created_at",
            "digest_issue_id",
            "channel",
            "created_at",
        ),
        Index(
            "ix_digest_delivery_decisions_user_channel_created_at",
            "user_id",
            "channel",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    digest_issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("pulse_digest_issues.id", ondelete="CASCADE")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False),
        nullable=False,
    )
    subscription_policy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscription_policies.id", ondelete="SET NULL")
    )
    dispatch_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("digest_dispatch_runs.id", ondelete="SET NULL")
    )
    decision: Mapped[DigestDeliveryDecisionStatus] = mapped_column(
        Enum(DigestDeliveryDecisionStatus, native_enum=False),
        nullable=False,
    )
    reason_codes: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    effective_timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    local_issue_weekday: Mapped[int | None] = mapped_column(Integer)
    selected_card_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    focus_card_type: Mapped[str | None] = mapped_column(String(100))
    quiet_hours: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    digest_issue: Mapped[PulseDigestIssue] = relationship(back_populates="delivery_decisions")
    user: Mapped[UserProfile] = relationship(back_populates="digest_delivery_decisions")
    subscription_policy: Mapped[SubscriptionPolicy | None] = relationship()
    dispatch_run: Mapped[DigestDispatchRun | None] = relationship(
        back_populates="delivery_decisions"
    )


class DigestPublicationAttempt(Base):
    __tablename__ = "digest_publication_attempts"
    __table_args__ = (
        UniqueConstraint(
            "digest_publication_job_id",
            "attempt_number",
            name="uq_digest_publication_attempts_job_attempt",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    digest_publication_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("digest_publication_jobs.id", ondelete="CASCADE")
    )
    dispatch_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("digest_dispatch_runs.id", ondelete="SET NULL")
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_mode: Mapped[OfficialAccountProviderMode] = mapped_column(
        Enum(OfficialAccountProviderMode, native_enum=False),
        nullable=False,
    )
    status: Mapped[DigestPublicationAttemptStatus] = mapped_column(
        Enum(DigestPublicationAttemptStatus, native_enum=False),
        nullable=False,
    )
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    error_summary: Mapped[str | None] = mapped_column(Text)
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    provider_response_code: Mapped[str | None] = mapped_column(String(100))
    provider_response_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    digest_publication_job: Mapped[DigestPublicationJob] = relationship(back_populates="attempts")
    dispatch_run: Mapped[DigestDispatchRun | None] = relationship(back_populates="attempts")


class OfficialAccountCallbackEvent(Base):
    __tablename__ = "official_account_callback_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    app_id: Mapped[str | None] = mapped_column(String(255))
    to_user_name: Mapped[str | None] = mapped_column(String(255))
    from_openid: Mapped[str | None] = mapped_column(String(255))
    msg_type: Mapped[str | None] = mapped_column(String(100))
    event_type: Mapped[str | None] = mapped_column(String(100))
    event_key: Mapped[str | None] = mapped_column(String(255))
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    signature_valid: Mapped[bool] = mapped_column(nullable=False, default=False)
    payload_format: Mapped[OfficialAccountCallbackPayloadFormat] = mapped_column(
        Enum(OfficialAccountCallbackPayloadFormat, native_enum=False),
        nullable=False,
        default=OfficialAccountCallbackPayloadFormat.UNKNOWN,
    )
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_payload_json: Mapped[dict[str, Any] | None] = mapped_column(
        "parsed_payload",
        JSON_VARIANT,
    )
    processing_status: Mapped[OfficialAccountCallbackProcessingStatus] = mapped_column(
        Enum(OfficialAccountCallbackProcessingStatus, native_enum=False),
        nullable=False,
        default=OfficialAccountCallbackProcessingStatus.ACCEPTED,
    )
    processing_note: Mapped[str | None] = mapped_column(Text)
    linked_binding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wechat_identity_bindings.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    linked_binding: Mapped[WeChatIdentityBinding | None] = relationship(
        back_populates="callback_events"
    )
    matched_handshake_sessions: Mapped[list[OfficialAccountBindingHandshakeSession]] = relationship(
        back_populates="matched_callback_event",
        foreign_keys="OfficialAccountBindingHandshakeSession.matched_callback_event_id",
    )


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


class ClientDevice(TimestampMixin, Base):
    __tablename__ = "client_devices"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    client_type: Mapped[ClientType] = mapped_column(
        Enum(ClientType, native_enum=False),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserProfile] = relationship(back_populates="client_devices")
    access_tokens: Mapped[list[ClientAccessToken]] = relationship(
        back_populates="client_device",
        cascade="all, delete-orphan",
        order_by="ClientAccessToken.issued_at.desc()",
    )
    cursor: Mapped[SyncCursor | None] = relationship(
        back_populates="client_device",
        cascade="all, delete-orphan",
        uselist=False,
    )
    mutations: Mapped[list[SyncMutation]] = relationship(
        back_populates="client_device",
        cascade="all, delete-orphan",
        order_by="SyncMutation.created_at.asc()",
    )


class ClientAccessToken(Base):
    __tablename__ = "client_access_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("client_devices.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_ip: Mapped[str | None] = mapped_column(String(255))
    user_agent: Mapped[str | None] = mapped_column(String(500))

    client_device: Mapped[ClientDevice] = relationship(back_populates="access_tokens")


class SyncEvent(Base):
    __tablename__ = "sync_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[SyncEventType] = mapped_column(
        Enum(SyncEventType, native_enum=False),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    event_source: Mapped[SyncEventSource] = mapped_column(
        Enum(SyncEventSource, native_enum=False),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[UserProfile] = relationship(back_populates="sync_events")


class SyncCursor(Base):
    __tablename__ = "sync_cursors"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("client_devices.id", ondelete="CASCADE"),
        unique=True,
    )
    last_event_sequence: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    client_device: Mapped[ClientDevice] = relationship(back_populates="cursor")


class SyncMutation(Base):
    __tablename__ = "sync_mutations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("client_devices.id", ondelete="CASCADE")
    )
    client_mutation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    mutation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    status: Mapped[SyncMutationStatus] = mapped_column(
        Enum(SyncMutationStatus, native_enum=False),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    resulting_event_sequence: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client_device: Mapped[ClientDevice] = relationship(back_populates="mutations")


class WorkActivityEvent(Base):
    __tablename__ = "work_activity_events"
    __table_args__ = (
        Index("ix_work_activity_events_user_happened_at", "user_id", "happened_at"),
        Index("ix_work_activity_events_paper_happened_at", "paper_id", "happened_at"),
        Index("ix_work_activity_events_activity_type", "activity_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    paper_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_profiles.id", ondelete="SET NULL")
    )
    activity_type: Mapped[WorkActivityType] = mapped_column(
        Enum(WorkActivityType, native_enum=False),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON_VARIANT)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[WorkActivitySource] = mapped_column(
        Enum(WorkActivitySource, native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[UserProfile] = relationship(back_populates="work_activity_events")
    paper: Mapped[PaperProfile | None] = relationship(back_populates="work_activity_events")


class ResearchWatchProfile(TimestampMixin, Base):
    __tablename__ = "research_watch_profiles"
    __table_args__ = (
        Index("ix_research_watch_profiles_user_enabled", "user_id", "enabled"),
        Index("ix_research_watch_profiles_paper", "paper_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    paper_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_profiles.id", ondelete="SET NULL")
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    source_mode: Mapped[ResearchWatchProfileSourceMode] = mapped_column(
        Enum(ResearchWatchProfileSourceMode, native_enum=False),
        nullable=False,
        default=ResearchWatchProfileSourceMode.MANUAL,
    )
    topics: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    venues: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    authors_of_interest: Mapped[list[str] | None] = mapped_column(JSON_VARIANT)

    user: Mapped[UserProfile] = relationship(back_populates="research_watch_profiles")
    paper: Mapped[PaperProfile | None] = relationship(back_populates="research_watch_profiles")
    external_retrieval_plans: Mapped[list[ExternalRetrievalPlan]] = relationship(
        back_populates="watch_profile",
    )


class ExternalRetrievalPlan(TimestampMixin, Base):
    __tablename__ = "external_retrieval_plans"
    __table_args__ = (
        Index(
            "ix_external_retrieval_plans_user_source",
            "user_id",
            "source_kind",
            "created_at",
        ),
        Index("ix_external_retrieval_plans_scope", "retrieval_scope"),
        Index("ix_external_retrieval_plans_paper", "paper_id"),
        Index("ix_external_retrieval_plans_watch_profile", "watch_profile_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_kind: Mapped[ExternalRetrievalSourceKind] = mapped_column(
        Enum(ExternalRetrievalSourceKind, native_enum=False),
        nullable=False,
    )
    retrieval_scope: Mapped[ExternalRetrievalScope] = mapped_column(
        Enum(ExternalRetrievalScope, native_enum=False),
        nullable=False,
    )
    watch_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_watch_profiles.id", ondelete="SET NULL")
    )
    paper_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_profiles.id", ondelete="SET NULL")
    )
    plan_label: Mapped[str] = mapped_column(String(255), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    effective_inputs: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    reason_codes: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[ExternalRetrievalPlanStatus] = mapped_column(
        Enum(ExternalRetrievalPlanStatus, native_enum=False),
        nullable=False,
        default=ExternalRetrievalPlanStatus.PLANNED,
    )

    user: Mapped[UserProfile] = relationship(back_populates="external_retrieval_plans")
    watch_profile: Mapped[ResearchWatchProfile | None] = relationship(
        back_populates="external_retrieval_plans"
    )
    paper: Mapped[PaperProfile | None] = relationship(back_populates="external_retrieval_plans")
    runs: Mapped[list[ExternalRetrievalRun]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ExternalRetrievalRun.created_at.desc()",
    )
    results: Mapped[list[ExternalRetrievedRecord]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ExternalRetrievedRecord.sort_order",
    )


class ExternalRetrievalRun(TimestampMixin, Base):
    __tablename__ = "external_retrieval_runs"
    __table_args__ = (
        Index(
            "ix_external_retrieval_runs_plan_status",
            "plan_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_external_retrieval_runs_user_source",
            "user_id",
            "source_kind",
            "created_at",
        ),
        Index("ix_external_retrieval_runs_scope", "retrieval_scope"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("external_retrieval_plans.id", ondelete="CASCADE")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_kind: Mapped[ExternalRetrievalSourceKind] = mapped_column(
        Enum(ExternalRetrievalSourceKind, native_enum=False),
        nullable=False,
    )
    retrieval_scope: Mapped[ExternalRetrievalScope] = mapped_column(
        Enum(ExternalRetrievalScope, native_enum=False),
        nullable=False,
    )
    status: Mapped[ExternalRetrievalRunStatus] = mapped_column(
        Enum(ExternalRetrievalRunStatus, native_enum=False),
        nullable=False,
        default=ExternalRetrievalRunStatus.PENDING,
    )
    request_url: Mapped[str | None] = mapped_column(Text)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    response_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT)
    raw_result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    normalized_result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[ExternalRetrievalPlan] = relationship(back_populates="runs")
    user: Mapped[UserProfile] = relationship(back_populates="external_retrieval_runs")
    results: Mapped[list[ExternalRetrievedRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ExternalRetrievedRecord.sort_order",
    )


class ExternalRetrievedRecord(TimestampMixin, Base):
    __tablename__ = "external_retrieved_records"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "external_id",
            name="uq_external_retrieved_records_run_external_id",
        ),
        Index(
            "ix_external_retrieved_records_user_source",
            "user_id",
            "source_kind",
            "created_at",
        ),
        Index("ix_external_retrieved_records_run_sort", "run_id", "sort_order"),
        Index("ix_external_retrieved_records_plan", "plan_id"),
        Index("ix_external_retrieved_records_scope", "retrieval_scope"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("external_retrieval_runs.id", ondelete="CASCADE")
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("external_retrieval_plans.id", ondelete="CASCADE")
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_kind: Mapped[ExternalRetrievalSourceKind] = mapped_column(
        Enum(ExternalRetrievalSourceKind, native_enum=False),
        nullable=False,
    )
    retrieval_scope: Mapped[ExternalRetrievalScope] = mapped_column(
        Enum(ExternalRetrievalScope, native_enum=False),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)
    doi: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract_snippet: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    publication_date: Mapped[str | None] = mapped_column(String(64))
    source_title: Mapped[str | None] = mapped_column(String(500))
    authors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON_VARIANT)
    matched_reason_codes: Mapped[list[str] | None] = mapped_column(JSON_VARIANT)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    run: Mapped[ExternalRetrievalRun] = relationship(back_populates="results")
    plan: Mapped[ExternalRetrievalPlan] = relationship(back_populates="results")
    user: Mapped[UserProfile] = relationship(back_populates="external_retrieval_results")
