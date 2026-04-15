"""Application settings."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from research_pulse_cn.domain.enums import (
    ExternalRetrievalMode,
    ExternalRetrievalSourceKind,
    OfficialAccountProviderMode,
    OfficialAccountTransportKind,
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
