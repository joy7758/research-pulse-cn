"""Domain enums shared across persistence, APIs, and services."""

from enum import StrEnum


class PaperType(StrEnum):
    PUBLISHED = "published"
    UNDER_REVIEW = "under_review"
    REVISION = "revision"
    IN_PREP = "in_prep"
    PAUSED = "paused"


class SignalSource(StrEnum):
    CNKI = "CNKI"
    WANFANG = "WANFANG"
    CQVIP = "CQVIP"
    READPAPER = "READPAPER"
    GOOGLE_SCHOLAR = "GOOGLE_SCHOLAR"
    MANUAL = "MANUAL"


class ChannelType(StrEnum):
    IN_APP = "in_app"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    EMAIL = "email"
    WEBHOOK = "webhook"


class SubscriptionFrequency(StrEnum):
    DAILY = "daily"
    EVENT = "event"


class PulseJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PulseJobScheduledReason(StrEnum):
    MANUAL_RUN = "manual_run"
    DAILY_SCHEDULE = "daily_schedule"
    REPLAY = "replay"


class PulseCardType(StrEnum):
    SIGNAL_CHANGE = "signal_change"
    STALLED_PROGRESS = "stalled_progress"
    DEADLINE_RISK = "deadline_risk"
    NEXT_ACTION = "next_action"
    RELATED_PAPER = "related_paper"


class DeliveryJobStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class WorkerRole(StrEnum):
    SCHEDULER = "scheduler"
    DELIVERY_WORKER = "delivery_worker"


class WorkerStatus(StrEnum):
    STARTING = "starting"
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class DeliveryAttemptStatus(StrEnum):
    STARTED = "started"
    SENT = "sent"
    FAILED = "failed"


class AdminRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AuditActorType(StrEnum):
    ADMIN = "admin"
    SERVICE = "service"
    ANONYMOUS = "anonymous"


class ClientType(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class SyncEventType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    SNAPSHOT = "snapshot"


class SyncEventSource(StrEnum):
    API = "api"
    SYNC_PUSH = "sync_push"
    WORKER = "worker"
    SEED = "seed"
    SYSTEM = "system"


class SyncMutationStatus(StrEnum):
    ACCEPTED = "accepted"
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class WeChatBindingChannelType(StrEnum):
    OFFICIAL_ACCOUNT = "official_account"
    MINI_PROGRAM = "mini_program"


class WeChatBindingState(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class PulseDigestIssueStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"


class DigestPublicationTarget(StrEnum):
    OFFICIAL_ACCOUNT = "official_account"


class DigestPublicationStatus(StrEnum):
    PENDING = "pending"
    PREPARED = "prepared"
    PREVIEWED = "previewed"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class DigestPublicationMode(StrEnum):
    MANUAL_PREVIEW = "manual_preview"
    SCHEDULED_PREPARE = "scheduled_prepare"
    FUTURE_PROVIDER = "future_provider"


ACTIVE_DELIVERY_CHANNELS = frozenset(
    {
        ChannelType.IN_APP,
        ChannelType.EMAIL,
        ChannelType.WEBHOOK,
    }
)

DEPRECATED_DELIVERY_CHANNELS = frozenset(
    {
        ChannelType.DINGTALK,
        ChannelType.WECHAT,
    }
)
