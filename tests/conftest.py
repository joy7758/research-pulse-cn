from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from research_pulse_cn import db as _db  # noqa: F401
from research_pulse_cn.app import create_app
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.db import models as _models  # noqa: F401
from research_pulse_cn.db.base import Base
from research_pulse_cn.db.session import get_engine, get_session_factory, reset_db_session_state


@pytest.fixture(autouse=True)
def isolated_test_environment(tmp_path, monkeypatch) -> Iterator[None]:
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("APP_MAX_DELIVERY_RETRIES", "2")
    monkeypatch.setenv("APP_DELIVERY_RETRY_DELAY_SECONDS", "0")
    get_settings.cache_clear()
    get_metrics().reset()
    reset_db_session_state()
    Base.metadata.create_all(bind=get_engine())
    yield
    Base.metadata.drop_all(bind=get_engine())
    reset_db_session_state()
    get_metrics().reset()
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def session() -> Iterator:
    db_session = get_session_factory()()
    try:
        yield db_session
    finally:
        db_session.close()
