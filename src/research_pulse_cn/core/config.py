"""Application settings."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from research_pulse_cn.domain.enums import (
    ExternalRetrievalMode,
    ExternalRetrievalSourceKind,
    GroupWorkspaceMemberRole,
    OfficialAccountOAuthScope,
    OfficialAccountProviderMode,
    OfficialAccountTransportKind,
    ResultShareKind,
)


class Settings(BaseSettings):
    """Environment-driven runtime settings."""

    app_name: str = Field(default="Research Pulse CN", validation_alias="APP_NAME")
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    app_log_level: str = Field(default="INFO", validation_alias="APP_LOG_LEVEL")
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    database_url_override: str | None = Field(default=None, validation_alias="APP_DATABASE_URL")
    max_delivery_retries: int = Field(default=3, validation_alias="APP_MAX_DELIVERY_RETRIES")
    delivery_retry_delay_seconds: int = Field(
        default=300, validation_alias="APP_DELIVERY_RETRY_DELAY_SECONDS"
    )
    pulse_stale_days: int = Field(default=10, validation_alias="APP_PULSE_STALE_DAYS")
    pulse_deadline_horizon_days: int = Field(
        default=7, validation_alias="APP_PULSE_DEADLINE_HORIZON_DAYS"
    )
    pulse_dedupe_window_hours: int = Field(
        default=24, validation_alias="APP_PULSE_DEDUPE_WINDOW_HOURS"
    )
    pulse_min_score: int = Field(default=10, validation_alias="APP_PULSE_MIN_SCORE")
    pulse_default_max_cards_per_run: int = Field(
        default=3, validation_alias="APP_PULSE_DEFAULT_MAX_CARDS_PER_RUN"
    )
    pulse_weight_signal_change: int = Field(
        default=18, validation_alias="APP_PULSE_WEIGHT_SIGNAL_CHANGE"
    )
    pulse_weight_stalled_progress: int = Field(
        default=12, validation_alias="APP_PULSE_WEIGHT_STALLED_PROGRESS"
    )
    pulse_weight_deadline_risk: int = Field(
        default=5, validation_alias="APP_PULSE_WEIGHT_DEADLINE_RISK"
    )
    pulse_weight_today_suggestion: int = Field(
        default=6, validation_alias="APP_PULSE_WEIGHT_TODAY_SUGGESTION"
    )
    pulse_weight_next_action: int = Field(
        default=8, validation_alias="APP_PULSE_WEIGHT_NEXT_ACTION"
    )
    pulse_weight_yesterday_summary: int = Field(
        default=10, validation_alias="APP_PULSE_WEIGHT_YESTERDAY_SUMMARY"
    )
    pulse_weight_related_paper: int = Field(
        default=4, validation_alias="APP_PULSE_WEIGHT_RELATED_PAPER"
    )
    pulse_yesterday_summary_min_events: int = Field(
        default=1, validation_alias="APP_PULSE_YESTERDAY_SUMMARY_MIN_EVENTS"
    )
    pulse_today_suggestion_stale_days_threshold: int = Field(
        default=5, validation_alias="APP_PULSE_TODAY_SUGGESTION_STALE_DAYS_THRESHOLD"
    )
    pulse_modifier_recent_signal_delta: int = Field(
        default=8, validation_alias="APP_PULSE_MODIFIER_RECENT_SIGNAL_DELTA"
    )
    pulse_modifier_approaching_deadline: int = Field(
        default=10, validation_alias="APP_PULSE_MODIFIER_APPROACHING_DEADLINE"
    )
    pulse_modifier_long_stagnation: int = Field(
        default=6, validation_alias="APP_PULSE_MODIFIER_LONG_STAGNATION"
    )
    pulse_modifier_explicit_next_action: int = Field(
        default=4, validation_alias="APP_PULSE_MODIFIER_EXPLICIT_NEXT_ACTION"
    )
    pulse_modifier_today_suggestion_priority: int = Field(
        default=1, validation_alias="APP_PULSE_MODIFIER_TODAY_SUGGESTION_PRIORITY"
    )
    pulse_modifier_today_suggestion_has_next_action: int = Field(
        default=3,
        validation_alias="APP_PULSE_MODIFIER_TODAY_SUGGESTION_HAS_NEXT_ACTION",
    )
    pulse_modifier_today_suggestion_revision_stage: int = Field(
        default=3,
        validation_alias="APP_PULSE_MODIFIER_TODAY_SUGGESTION_REVISION_STAGE",
    )
    pulse_modifier_today_suggestion_stale_progress: int = Field(
        default=3,
        validation_alias="APP_PULSE_MODIFIER_TODAY_SUGGESTION_STALE_PROGRESS",
    )
    pulse_modifier_today_suggestion_blocker_present: int = Field(
        default=4,
        validation_alias="APP_PULSE_MODIFIER_TODAY_SUGGESTION_BLOCKER_PRESENT",
    )
    pulse_modifier_yesterday_summary_activity_diversity: int = Field(
        default=3,
        validation_alias="APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_ACTIVITY_DIVERSITY",
    )
    pulse_modifier_yesterday_summary_multi_paper: int = Field(
        default=4,
        validation_alias="APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_MULTI_PAPER",
    )
    pulse_modifier_related_paper_has_doi: int = Field(
        default=2,
        validation_alias="APP_PULSE_MODIFIER_RELATED_PAPER_HAS_DOI",
    )
    pulse_modifier_related_paper_match_reason_count: int = Field(
        default=1,
        validation_alias="APP_PULSE_MODIFIER_RELATED_PAPER_MATCH_REASON_COUNT",
    )
    pulse_modifier_related_paper_linked_paper: int = Field(
        default=3,
        validation_alias="APP_PULSE_MODIFIER_RELATED_PAPER_LINKED_PAPER",
    )
    pulse_modifier_related_paper_recent_retrieval: int = Field(
        default=2,
        validation_alias="APP_PULSE_MODIFIER_RELATED_PAPER_RECENT_RETRIEVAL",
    )
    pulse_related_paper_lookback_days: int = Field(
        default=14,
        validation_alias="APP_PULSE_RELATED_PAPER_LOOKBACK_DAYS",
    )
    pulse_related_paper_max_candidates_per_run: int = Field(
        default=3,
        validation_alias="APP_PULSE_RELATED_PAPER_MAX_CANDIDATES_PER_RUN",
    )
    pulse_related_paper_dedupe_days: int = Field(
        default=7,
        validation_alias="APP_PULSE_RELATED_PAPER_DEDUPE_DAYS",
    )
    external_retrieval_mode: ExternalRetrievalMode = Field(
        default=ExternalRetrievalMode.DISABLED,
        validation_alias="APP_EXTERNAL_RETRIEVAL_MODE",
    )
    external_retrieval_enabled_sources: str = Field(
        default="openalex,crossref,arxiv",
        validation_alias="APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES",
    )
    external_retrieval_max_plans_per_user: int = Field(
        default=6,
        validation_alias="APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER",
    )
    external_retrieval_max_keywords_per_plan: int = Field(
        default=4,
        validation_alias="APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN",
    )
    external_retrieval_max_topics_per_plan: int = Field(
        default=3,
        validation_alias="APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN",
    )
    external_retrieval_lookback_days_for_activity_context: int = Field(
        default=7,
        validation_alias="APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT",
    )
    external_retrieval_http_connect_timeout_seconds: int = Field(
        default=5,
        validation_alias="APP_EXTERNAL_RETRIEVAL_HTTP_CONNECT_TIMEOUT_SECONDS",
    )
    external_retrieval_http_read_timeout_seconds: int = Field(
        default=10,
        validation_alias="APP_EXTERNAL_RETRIEVAL_HTTP_READ_TIMEOUT_SECONDS",
    )
    external_retrieval_max_results_per_plan: int = Field(
        default=5,
        validation_alias="APP_EXTERNAL_RETRIEVAL_MAX_RESULTS_PER_PLAN",
    )
    external_retrieval_execution_dedupe_minutes: int = Field(
        default=60,
        validation_alias="APP_EXTERNAL_RETRIEVAL_EXECUTION_DEDUPE_MINUTES",
    )
    external_retrieval_openalex_api_key: str | None = Field(
        default=None,
        validation_alias="APP_EXTERNAL_RETRIEVAL_OPENALEX_API_KEY",
    )
    external_retrieval_crossref_mailto: str | None = Field(
        default=None,
        validation_alias="APP_EXTERNAL_RETRIEVAL_CROSSREF_MAILTO",
    )
    external_retrieval_crossref_user_agent_app_name: str | None = Field(
        default=None,
        validation_alias="APP_EXTERNAL_RETRIEVAL_CROSSREF_USER_AGENT_APP_NAME",
    )
    default_timezone: str = Field(default="UTC", validation_alias="APP_DEFAULT_TIMEZONE")
    pulse_default_send_hour_local: int = Field(
        default=9, validation_alias="APP_PULSE_DEFAULT_SEND_HOUR_LOCAL"
    )
    pulse_default_send_minute_local: int = Field(
        default=0, validation_alias="APP_PULSE_DEFAULT_SEND_MINUTE_LOCAL"
    )
    worker_heartbeat_interval_seconds: int = Field(
        default=15, validation_alias="APP_WORKER_HEARTBEAT_INTERVAL_SECONDS"
    )
    worker_lease_seconds: int = Field(default=120, validation_alias="APP_WORKER_LEASE_SECONDS")
    auth_access_token_ttl_minutes: int = Field(
        default=30,
        validation_alias="APP_AUTH_ACCESS_TOKEN_TTL_MINUTES",
    )
    auth_refresh_token_ttl_days: int = Field(
        default=14,
        validation_alias="APP_AUTH_REFRESH_TOKEN_TTL_DAYS",
    )
    auth_jwt_secret: str = Field(
        default="change-me-for-production",
        validation_alias="APP_AUTH_JWT_SECRET",
    )
    auth_jwt_issuer: str = Field(
        default="research-pulse-cn",
        validation_alias="APP_AUTH_JWT_ISSUER",
    )
    auth_jwt_audience: str = Field(
        default="research-pulse-cn-admin",
        validation_alias="APP_AUTH_JWT_AUDIENCE",
    )
    internal_service_token: str = Field(
        default="change-me-internal-service-token",
        validation_alias="APP_INTERNAL_SERVICE_TOKEN",
    )
    sync_device_token_ttl_days: int = Field(
        default=90,
        validation_alias="APP_SYNC_DEVICE_TOKEN_TTL_DAYS",
    )
    sync_feed_default_limit: int = Field(
        default=100,
        validation_alias="APP_SYNC_FEED_DEFAULT_LIMIT",
    )
    sync_feed_max_limit: int = Field(
        default=500,
        validation_alias="APP_SYNC_FEED_MAX_LIMIT",
    )
    sync_push_max_batch_size: int = Field(
        default=50,
        validation_alias="APP_SYNC_PUSH_MAX_BATCH_SIZE",
    )
    mini_read_grant_default_ttl_hours: int = Field(
        default=72,
        validation_alias="APP_MINI_READ_GRANT_DEFAULT_TTL_HOURS",
    )
    mini_papers_default_limit: int = Field(
        default=20,
        validation_alias="APP_MINI_PAPERS_DEFAULT_LIMIT",
    )
    mini_papers_max_limit: int = Field(
        default=100,
        validation_alias="APP_MINI_PAPERS_MAX_LIMIT",
    )
    subscription_editor_web_allowed_origins: str = Field(
        default=(
            "http://127.0.0.1:5173,http://localhost:5173,"
            "http://127.0.0.1:4173,http://localhost:4173"
        ),
        validation_alias="APP_SUBSCRIPTION_EDITOR_WEB_ALLOWED_ORIGINS",
    )
    result_share_web_allowed_origins: str = Field(
        default=(
            "http://127.0.0.1:5174,http://localhost:5174,"
            "http://127.0.0.1:4174,http://localhost:4174"
        ),
        validation_alias="APP_RESULT_SHARE_WEB_ALLOWED_ORIGINS",
    )
    group_workspace_admin_web_allowed_origins: str = Field(
        default=(
            "http://127.0.0.1:5175,http://localhost:5175,"
            "http://127.0.0.1:4175,http://localhost:4175"
        ),
        validation_alias="APP_GROUP_WORKSPACE_ADMIN_WEB_ALLOWED_ORIGINS",
    )
    user_workbench_admin_web_allowed_origins: str = Field(
        default=(
            "http://127.0.0.1:5176,http://localhost:5176,"
            "http://127.0.0.1:4176,http://localhost:4176"
        ),
        validation_alias="APP_USER_WORKBENCH_ADMIN_WEB_ALLOWED_ORIGINS",
    )
    group_workspace_invite_web_allowed_origins: str = Field(
        default=(
            "http://127.0.0.1:5177,http://localhost:5177,"
            "http://127.0.0.1:4177,http://localhost:4177"
        ),
        validation_alias="APP_GROUP_WORKSPACE_INVITE_WEB_ALLOWED_ORIGINS",
    )
    group_workspace_invites_enabled: bool = Field(
        default=False,
        validation_alias="APP_GROUP_WORKSPACE_INVITES_ENABLED",
    )
    group_workspace_invite_default_max_claims: int = Field(
        default=1,
        validation_alias="APP_GROUP_WORKSPACE_INVITE_DEFAULT_MAX_CLAIMS",
    )
    group_workspace_invite_ttl_hours: int = Field(
        default=72,
        validation_alias="APP_GROUP_WORKSPACE_INVITE_TTL_HOURS",
    )
    group_workspace_invite_public_bootstrap_enabled: bool = Field(
        default=True,
        validation_alias="APP_GROUP_WORKSPACE_INVITE_PUBLIC_BOOTSTRAP_ENABLED",
    )
    group_workspace_result_collect_enabled: bool = Field(
        default=False,
        validation_alias="APP_GROUP_WORKSPACE_RESULT_COLLECT_ENABLED",
    )
    group_workspace_result_collect_allowed_share_kinds: str = Field(
        default="digest_issue,paper_snapshot",
        validation_alias="APP_GROUP_WORKSPACE_RESULT_COLLECT_ALLOWED_SHARE_KINDS",
    )
    group_workspace_result_collect_allowed_roles: str = Field(
        default="owner,editor",
        validation_alias="APP_GROUP_WORKSPACE_RESULT_COLLECT_ALLOWED_ROLES",
    )
    group_workspace_result_collect_max_papers_per_digest: int = Field(
        default=10,
        validation_alias="APP_GROUP_WORKSPACE_RESULT_COLLECT_MAX_PAPERS_PER_DIGEST",
    )
    subscription_editor_handoff_enabled: bool = Field(
        default=False,
        validation_alias="APP_SUBSCRIPTION_EDITOR_HANDOFF_ENABLED",
    )
    subscription_editor_handoff_ttl_minutes: int = Field(
        default=15,
        validation_alias="APP_SUBSCRIPTION_EDITOR_HANDOFF_TTL_MINUTES",
    )
    subscription_editor_handoff_require_active_self_service_grant: bool = Field(
        default=True,
        validation_alias="APP_SUBSCRIPTION_EDITOR_HANDOFF_REQUIRE_ACTIVE_SELF_SERVICE_GRANT",
    )
    subscription_editor_handoff_require_channel_binding: bool = Field(
        default=False,
        validation_alias="APP_SUBSCRIPTION_EDITOR_HANDOFF_REQUIRE_CHANNEL_BINDING",
    )
    digest_signal_updates_max_items: int = Field(
        default=2,
        validation_alias="APP_DIGEST_SIGNAL_UPDATES_MAX_ITEMS",
    )
    digest_related_papers_max_items: int = Field(
        default=2,
        validation_alias="APP_DIGEST_RELATED_PAPERS_MAX_ITEMS",
    )
    digest_other_updates_max_items: int = Field(
        default=3,
        validation_alias="APP_DIGEST_OTHER_UPDATES_MAX_ITEMS",
    )
    digest_auto_prepare_official_account: bool = Field(
        default=False,
        validation_alias="APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT",
    )
    digest_auto_dispatch_official_account: bool = Field(
        default=False,
        validation_alias="APP_DIGEST_AUTO_DISPATCH_OFFICIAL_ACCOUNT",
    )
    digest_dispatch_max_publication_jobs_per_run: int = Field(
        default=20,
        validation_alias="APP_DIGEST_DISPATCH_MAX_PUBLICATION_JOBS_PER_RUN",
    )
    digest_dispatch_retry_failed_jobs: bool = Field(
        default=False,
        validation_alias="APP_DIGEST_DISPATCH_RETRY_FAILED_JOBS",
    )
    digest_dispatch_prepare_if_missing: bool = Field(
        default=False,
        validation_alias="APP_DIGEST_DISPATCH_PREPARE_IF_MISSING",
    )
    digest_auto_dispatch_require_real_mode: bool = Field(
        default=True,
        validation_alias="APP_DIGEST_AUTO_DISPATCH_REQUIRE_REAL_MODE",
    )
    official_account_provider_mode: OfficialAccountProviderMode = Field(
        default=OfficialAccountProviderMode.DISABLED,
        validation_alias="APP_OFFICIAL_ACCOUNT_PROVIDER_MODE",
    )
    official_account_transport_kind: OfficialAccountTransportKind = Field(
        default=OfficialAccountTransportKind.TEMPLATE_NOTICE,
        validation_alias="APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND",
    )
    wechat_official_app_id: str | None = Field(
        default=None,
        validation_alias="APP_WECHAT_OFFICIAL_APP_ID",
    )
    wechat_official_app_secret: str | None = Field(
        default=None,
        validation_alias="APP_WECHAT_OFFICIAL_APP_SECRET",
    )
    wechat_official_callback_token: str | None = Field(
        default=None,
        validation_alias="APP_WECHAT_OFFICIAL_CALLBACK_TOKEN",
    )
    wechat_official_callback_aes_key: str | None = Field(
        default=None,
        validation_alias="APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY",
    )
    wechat_official_digest_template_id: str | None = Field(
        default=None,
        validation_alias="APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID",
    )
    official_account_callback_enabled: bool = Field(
        default=False,
        validation_alias="APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED",
    )
    official_account_real_send_enabled: bool = Field(
        default=False,
        validation_alias="APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED",
    )
    official_account_access_token_refresh_skew_seconds: int = Field(
        default=120,
        validation_alias="APP_OFFICIAL_ACCOUNT_ACCESS_TOKEN_REFRESH_SKEW_SECONDS",
    )
    official_account_http_connect_timeout_seconds: int = Field(
        default=5,
        validation_alias="APP_OFFICIAL_ACCOUNT_HTTP_CONNECT_TIMEOUT_SECONDS",
    )
    official_account_http_read_timeout_seconds: int = Field(
        default=10,
        validation_alias="APP_OFFICIAL_ACCOUNT_HTTP_READ_TIMEOUT_SECONDS",
    )
    official_account_max_retries: int = Field(
        default=2,
        validation_alias="APP_OFFICIAL_ACCOUNT_MAX_RETRIES",
    )
    official_account_template_field_mapping_json: dict[str, str] | None = Field(
        default=None,
        validation_alias="APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON",
    )
    official_account_default_mini_program_app_id: str | None = Field(
        default=None,
        validation_alias="APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID",
    )
    official_account_default_article_base_url: str | None = Field(
        default=None,
        validation_alias="APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL",
    )
    official_account_dispatch_timeout_seconds: int = Field(
        default=5,
        validation_alias="APP_OFFICIAL_ACCOUNT_DISPATCH_TIMEOUT_SECONDS",
    )
    official_account_binding_handshake_ttl_minutes: int = Field(
        default=30,
        validation_alias="APP_OFFICIAL_ACCOUNT_BINDING_HANDSHAKE_TTL_MINUTES",
    )
    official_account_binding_reconciliation_lookback_hours: int = Field(
        default=72,
        validation_alias="APP_OFFICIAL_ACCOUNT_BINDING_RECONCILIATION_LOOKBACK_HOURS",
    )
    official_account_binding_require_signature_valid: bool = Field(
        default=True,
        validation_alias="APP_OFFICIAL_ACCOUNT_BINDING_REQUIRE_SIGNATURE_VALID",
    )
    official_account_binding_default_digest_enabled: bool = Field(
        default=True,
        validation_alias="APP_OFFICIAL_ACCOUNT_BINDING_DEFAULT_DIGEST_ENABLED",
    )
    official_account_oauth_enabled: bool = Field(
        default=False,
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_ENABLED",
    )
    official_account_oauth_default_scope: OfficialAccountOAuthScope = Field(
        default=OfficialAccountOAuthScope.SNSAPI_BASE,
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_DEFAULT_SCOPE",
    )
    official_account_oauth_callback_public_base_url: str | None = Field(
        default=None,
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_CALLBACK_PUBLIC_BASE_URL",
    )
    official_account_oauth_callback_path: str = Field(
        default="/integrations/wechat/official-account/oauth/callback",
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_CALLBACK_PATH",
    )
    official_account_oauth_fetch_userinfo_when_scope_userinfo: bool = Field(
        default=True,
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_FETCH_USERINFO_WHEN_SCOPE_USERINFO",
    )
    official_account_oauth_lang: str = Field(
        default="zh_CN",
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_LANG",
    )
    official_account_oauth_success_redirect_url: str | None = Field(
        default=None,
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_SUCCESS_REDIRECT_URL",
    )
    official_account_oauth_failure_redirect_url: str | None = Field(
        default=None,
        validation_alias="APP_OFFICIAL_ACCOUNT_OAUTH_FAILURE_REDIRECT_URL",
    )

    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="research_pulse_cn", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="research_pulse", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="research_pulse", validation_alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Build the PostgreSQL DSN for future persistence wiring."""
        if self.database_url_override:
            return self.database_url_override
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        """Build the Redis connection URL for queue and cache integrations."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def external_retrieval_enabled_source_kinds(self) -> list[ExternalRetrievalSourceKind]:
        """Return enabled retrieval sources parsed from the environment string."""
        values: list[ExternalRetrievalSourceKind] = []
        seen: set[ExternalRetrievalSourceKind] = set()
        raw_values = str(self.external_retrieval_enabled_sources).replace(";", ",").split(",")
        for raw_value in raw_values:
            cleaned = raw_value.strip().lower()
            if not cleaned:
                continue
            try:
                source_kind = ExternalRetrievalSourceKind(cleaned)
            except ValueError:
                continue
            if source_kind in seen:
                continue
            seen.add(source_kind)
            values.append(source_kind)
        return values

    @property
    def subscription_editor_web_allowed_origin_list(self) -> list[str]:
        """Return allowed browser origins for the subscription editor shell."""
        values: list[str] = []
        seen: set[str] = set()
        raw_values = str(self.subscription_editor_web_allowed_origins).replace(";", ",").split(",")
        for raw_value in raw_values:
            cleaned = raw_value.strip().rstrip("/")
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            values.append(cleaned)
        return values

    @property
    def result_share_web_allowed_origin_list(self) -> list[str]:
        """Return allowed browser origins for the result share shell."""
        values: list[str] = []
        seen: set[str] = set()
        raw_values = str(self.result_share_web_allowed_origins).replace(";", ",").split(",")
        for raw_value in raw_values:
            cleaned = raw_value.strip().rstrip("/")
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            values.append(cleaned)
        return values

    @property
    def group_workspace_admin_web_allowed_origin_list(self) -> list[str]:
        """Return allowed browser origins for the group workspace admin shell."""
        values: list[str] = []
        seen: set[str] = set()
        raw_values = (
            str(self.group_workspace_admin_web_allowed_origins).replace(";", ",").split(",")
        )
        for raw_value in raw_values:
            cleaned = raw_value.strip().rstrip("/")
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            values.append(cleaned)
        return values

    @property
    def user_workbench_admin_web_allowed_origin_list(self) -> list[str]:
        """Return allowed browser origins for the user workbench admin shell."""
        values: list[str] = []
        seen: set[str] = set()
        raw_values = str(self.user_workbench_admin_web_allowed_origins).replace(";", ",").split(",")
        for raw_value in raw_values:
            cleaned = raw_value.strip().rstrip("/")
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            values.append(cleaned)
        return values

    @property
    def group_workspace_invite_web_allowed_origin_list(self) -> list[str]:
        """Return allowed browser origins for the group workspace invite shell."""
        values: list[str] = []
        seen: set[str] = set()
        raw_values = (
            str(self.group_workspace_invite_web_allowed_origins).replace(";", ",").split(",")
        )
        for raw_value in raw_values:
            cleaned = raw_value.strip().rstrip("/")
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            values.append(cleaned)
        return values

    @property
    def group_workspace_result_collect_allowed_share_kind_list(self) -> list[ResultShareKind]:
        """Return collectable share kinds parsed from configuration."""
        values: list[ResultShareKind] = []
        seen: set[ResultShareKind] = set()
        raw_values = (
            str(self.group_workspace_result_collect_allowed_share_kinds)
            .replace(";", ",")
            .split(",")
        )
        for raw_value in raw_values:
            cleaned = raw_value.strip().lower()
            if not cleaned:
                continue
            try:
                share_kind = ResultShareKind(cleaned)
            except ValueError:
                continue
            if share_kind in seen:
                continue
            seen.add(share_kind)
            values.append(share_kind)
        return values

    @property
    def group_workspace_result_collect_allowed_role_list(self) -> list[GroupWorkspaceMemberRole]:
        """Return workspace member roles allowed to collect shared results."""
        values: list[GroupWorkspaceMemberRole] = []
        seen: set[GroupWorkspaceMemberRole] = set()
        raw_values = (
            str(self.group_workspace_result_collect_allowed_roles).replace(";", ",").split(",")
        )
        for raw_value in raw_values:
            cleaned = raw_value.strip().lower()
            if not cleaned:
                continue
            try:
                role = GroupWorkspaceMemberRole(cleaned)
            except ValueError:
                continue
            if role in seen:
                continue
            seen.add(role)
            values.append(role)
        return values

    @property
    def browser_allowed_origin_list(self) -> list[str]:
        """Return combined loopback origins for thin browser shells."""
        values: list[str] = []
        seen: set[str] = set()
        for origin in (
            *self.subscription_editor_web_allowed_origin_list,
            *self.result_share_web_allowed_origin_list,
            *self.group_workspace_admin_web_allowed_origin_list,
            *self.user_workbench_admin_web_allowed_origin_list,
            *self.group_workspace_invite_web_allowed_origin_list,
        ):
            if origin in seen:
                continue
            seen.add(origin)
            values.append(origin)
        return values


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
