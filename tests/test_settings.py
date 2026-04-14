from research_pulse_cn.core.config import get_settings


def test_settings_builds_runtime_urls(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Research Pulse CN")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+pysqlite:///tmp/research-pulse-cn-test.db")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "research")
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_DB", "2")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.database_url == "sqlite+pysqlite:///tmp/research-pulse-cn-test.db"
    assert settings.redis_url == "redis://cache:6380/2"
