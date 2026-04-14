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
