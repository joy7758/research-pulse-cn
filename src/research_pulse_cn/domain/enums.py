"""Domain enums shared across persistence, APIs, and services."""

from enum import StrEnum


class PaperType(StrEnum):
    PUBLISHED = "published"
    UNDER_REVIEW = "under_review"
    REVISION = "revision"
    IN_PREP = "in_prep"
    PAUSED = "paused"


class PaperImportSourceFormat(StrEnum):
    CSL_JSON = "csl_json"
    BIBTEX = "bibtex"
    RIS = "ris"
    TABULAR = "tabular"
    PDF_FOLDER = "pdf_folder"


class PaperImportCommitRecordStatus(StrEnum):
    COMMITTED = "committed"
    SKIPPED = "skipped"
    FAILED = "failed"
    DRY_RUN = "dry_run"


class PaperReadingStatus(StrEnum):
    UNREAD = "unread"
    SKIMMING = "skimming"
    READING = "reading"
    READ = "read"
    ARCHIVED = "archived"


class PaperResearchStage(StrEnum):
    INBOX = "inbox"
    TRIAGE = "triage"
    RELEVANT = "relevant"
    REVIEWING = "reviewing"
    CITED = "cited"
    IMPLEMENTED = "implemented"
    PARKED = "parked"


class PaperPriorityLevel(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


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
    OFFICIAL_ACCOUNT = "official_account"
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
    TODAY_SUGGESTION = "today_suggestion"
    NEXT_ACTION = "next_action"
    YESTERDAY_SUMMARY = "yesterday_summary"
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


class WorkActivityType(StrEnum):
    PAPER_UPDATED = "paper_updated"
    PROGRESS_EVENT_CREATED = "progress_event_created"
    SUBSCRIPTION_POLICY_UPDATED = "subscription_policy_updated"
    ATTACHMENT_IMPORTED = "attachment_imported"
    NOTE_CREATED = "note_created"
    NOTE_SAVED = "note_saved"
    REVIEW_ROUND_CREATED = "review_round_created"
    REVIEWER_MATRIX_GENERATED = "reviewer_matrix_generated"
    RESPONSE_LETTER_GENERATED = "response_letter_generated"


class WorkActivitySource(StrEnum):
    API = "api"
    SYNC_MUTATION = "sync_mutation"
    DESKTOP_LOCAL = "desktop_local"
    SYSTEM = "system"


class ResearchWatchProfileSourceMode(StrEnum):
    MANUAL = "manual"
    PAPER_BOOTSTRAP = "paper_bootstrap"


class ExternalRetrievalMode(StrEnum):
    DISABLED = "disabled"
    PLAN_ONLY = "plan_only"
    EXECUTE = "execute"


class ExternalRetrievalSourceKind(StrEnum):
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    ARXIV = "arxiv"


class ExternalRetrievalScope(StrEnum):
    RELATED_PAPER = "related_paper"
    VENUE_UPDATE = "venue_update"
    AUTHOR_WATCH = "author_watch"


class ExternalRetrievalPlanStatus(StrEnum):
    PLANNED = "planned"
    PREVIEWED = "previewed"
    SKIPPED = "skipped"


class ExternalRetrievalRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


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


class DigestPublicationAttemptStatus(StrEnum):
    STARTED = "started"
    PREVIEWED = "previewed"
    SENT = "sent"
    FAILED = "failed"


class DigestDispatchMode(StrEnum):
    MANUAL = "manual"
    AUTO_AFTER_ORCHESTRATION = "auto_after_orchestration"
    RETRY_FAILED = "retry_failed"


class DigestDispatchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DigestDeliveryDecisionStatus(StrEnum):
    ELIGIBLE = "eligible"
    SKIPPED = "skipped"


class OfficialAccountProviderMode(StrEnum):
    DISABLED = "disabled"
    DRY_RUN = "dry_run"
    REAL = "real"


class OfficialAccountTransportKind(StrEnum):
    TEMPLATE_NOTICE = "template_notice"


class DesktopNotificationType(StrEnum):
    DAILY_RESEARCH_PULSE = "daily_research_pulse"


class DesktopNotificationUrgency(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class DesktopNotificationDeliveryState(StrEnum):
    DRAFT = "draft"
    NOT_SENT = "not_sent"


class DesktopNotificationActionKind(StrEnum):
    OPEN_DAILY_PULSE = "open_daily_pulse"
    OPEN_NEXT_ACTIONS = "open_next_actions"
    OPEN_METADATA_ATTENTION = "open_metadata_attention"
    OPEN_TRIAGE_QUEUE = "open_triage_queue"


class MiniProgramDetailType(StrEnum):
    DAILY_PULSE = "daily_pulse"
    PAPER = "paper"
    NEXT_ACTIONS = "next_actions"
    METADATA_ATTENTION = "metadata_attention"
    TRIAGE = "triage"


class MiniProgramDetailDeliveryState(StrEnum):
    PREVIEW = "preview"
    DRAFT = "draft"
    NOT_SENT = "not_sent"


class MiniProgramDetailCardType(StrEnum):
    OVERVIEW = "overview"
    TODAY_FOCUS = "today_focus"
    CONTINUE_READING = "continue_reading"
    NEXT_ACTIONS = "next_actions"
    METADATA_ATTENTION = "metadata_attention"
    TRIAGE = "triage"
    PAPER_DETAIL = "paper_detail"


class MiniProgramDetailActionKind(StrEnum):
    OPEN_DAILY_PULSE = "open_daily_pulse"
    OPEN_PAPER_DETAIL = "open_paper_detail"
    OPEN_NEXT_ACTIONS = "open_next_actions"
    OPEN_METADATA_ATTENTION = "open_metadata_attention"
    OPEN_TRIAGE = "open_triage"
    OPEN_PAPERS_LIST = "open_papers_list"


class OfficialAccountCallbackPayloadFormat(StrEnum):
    XML = "xml"
    JSON = "json"
    UNKNOWN = "unknown"


class OfficialAccountCallbackProcessingStatus(StrEnum):
    ACCEPTED = "accepted"
    PROCESSED = "processed"
    IGNORED = "ignored"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class MiniReadGrantType(StrEnum):
    PREVIEW = "preview"
    DIGEST_LANDING = "digest_landing"
    DAILY_OVERVIEW = "daily_overview"
    PAPER_DETAIL = "paper_detail"


class MiniReadGrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SubscriptionSelfServiceGrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SubscriptionEditorHandoffGrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SubscriptionEditorHandoffIssuedBy(StrEnum):
    MINI_HANDOFF = "mini_handoff"
    ADMIN = "admin"


class OfficialAccountOAuthScope(StrEnum):
    SNSAPI_BASE = "snsapi_base"
    SNSAPI_USERINFO = "snsapi_userinfo"


class OfficialAccountBindingHandshakeSessionStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    CLAIMED = "claimed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"
    CONFLICTED = "conflicted"


class GroupWorkspaceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class GroupWorkspaceMemberRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class GroupWorkspaceInviteRole(StrEnum):
    EDITOR = "editor"
    VIEWER = "viewer"


class GroupWorkspaceInviteGrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"


class GroupWorkspaceInviteClaimStatus(StrEnum):
    CLAIMED = "claimed"
    ALREADY_MEMBER = "already_member"
    REJECTED = "rejected"


class ResultShareKind(StrEnum):
    DIGEST_ISSUE = "digest_issue"
    PAPER_SNAPSHOT = "paper_snapshot"
    WORKSPACE_BOARD = "workspace_board"


class ResultShareGrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ResultShareAliasStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ResultShareViewAccessMode(StrEnum):
    SHARE_TOKEN = "share_token"
    ALIAS = "alias"
    ALIAS_REDIRECT = "alias_redirect"


class ResultShareViewEventType(StrEnum):
    BOOTSTRAP_VIEW = "bootstrap_view"
    CONTENT_VIEW = "content_view"
    REDIRECT = "redirect"
    INVITE_HANDOFF_REDIRECT = "invite_handoff_redirect"
    COLLECT_HANDOFF_REDIRECT = "collect_handoff_redirect"


class ResultShareViewOutcome(StrEnum):
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ResultShareHandoffTargetKind(StrEnum):
    GROUP_WORKSPACE_INVITE_ENTRY = "group_workspace_invite_entry"
    RESULT_SHARE_COLLECT_ENTRY = "result_share_collect_entry"


class GroupWorkspaceResultCollectStatus(StrEnum):
    COLLECTED = "collected"
    ALREADY_PRESENT = "already_present"
    REJECTED = "rejected"


ACTIVE_DELIVERY_CHANNELS = frozenset(
    {
        ChannelType.IN_APP,
        ChannelType.EMAIL,
        ChannelType.WEBHOOK,
        ChannelType.OFFICIAL_ACCOUNT,
    }
)

DEPRECATED_DELIVERY_CHANNELS = frozenset(
    {
        ChannelType.DINGTALK,
        ChannelType.WECHAT,
    }
)
