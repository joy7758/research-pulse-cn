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


def test_settings_parse_enabled_external_retrieval_sources(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+pysqlite:///tmp/research-pulse-cn-test.db")
    monkeypatch.setenv("APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES", "openalex, crossref ,arxiv")
    get_settings.cache_clear()

    settings = get_settings()

    assert [item.value for item in settings.external_retrieval_enabled_source_kinds] == [
        "openalex",
        "crossref",
        "arxiv",
    ]


def test_settings_include_group_workspace_invite_web_origins(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+pysqlite:///tmp/research-pulse-cn-test.db")
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_INVITE_WEB_ALLOWED_ORIGINS",
        "http://127.0.0.1:5177,http://localhost:5177/",
    )
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.group_workspace_invite_web_allowed_origin_list == [
        "http://127.0.0.1:5177",
        "http://localhost:5177",
    ]
    assert "http://127.0.0.1:5177" in settings.browser_allowed_origin_list


def test_settings_normalize_group_workspace_invite_entry_url(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+pysqlite:///tmp/research-pulse-cn-test.db")
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_INVITE_WEB_ENTRY_BASE_URL",
        "http://127.0.0.1:5177/",
    )
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.group_workspace_invite_web_entry_url == "http://127.0.0.1:5177"


def test_settings_parse_group_workspace_result_collect_lists(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+pysqlite:///tmp/research-pulse-cn-test.db")
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_RESULT_COLLECT_ALLOWED_SHARE_KINDS",
        "digest_issue, paper_snapshot, workspace_board",
    )
    monkeypatch.setenv(
        "APP_GROUP_WORKSPACE_RESULT_COLLECT_ALLOWED_ROLES",
        "owner, editor, viewer",
    )
    get_settings.cache_clear()

    settings = get_settings()

    assert [
        item.value
        for item in settings.group_workspace_result_collect_allowed_share_kind_list
    ] == [
        "digest_issue",
        "paper_snapshot",
        "workspace_board",
    ]
    assert [
        item.value for item in settings.group_workspace_result_collect_allowed_role_list
    ] == [
        "owner",
        "editor",
        "viewer",
    ]
