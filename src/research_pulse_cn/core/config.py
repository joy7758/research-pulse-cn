"""Application settings."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    pulse_weight_next_action: int = Field(
        default=8, validation_alias="APP_PULSE_WEIGHT_NEXT_ACTION"
    )
    pulse_weight_related_paper: int = Field(
        default=4, validation_alias="APP_PULSE_WEIGHT_RELATED_PAPER"
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
