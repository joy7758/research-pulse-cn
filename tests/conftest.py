from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from research_pulse_cn import db as _db  # noqa: F401
from research_pulse_cn.app import create_app
from research_pulse_cn.auth.crypto import hash_password
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.db import models as _models  # noqa: F401
from research_pulse_cn.db.base import Base
from research_pulse_cn.db.models import AdminAccount
from research_pulse_cn.db.session import get_engine, get_session_factory, reset_db_session_state
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.services.official_account import reset_official_account_runtime_state


@pytest.fixture(autouse=True)
def isolated_test_environment(tmp_path, monkeypatch) -> Iterator[None]:
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("APP_MAX_DELIVERY_RETRIES", "2")
    monkeypatch.setenv("APP_DELIVERY_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("APP_AUTH_JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("APP_AUTH_JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("APP_INTERNAL_SERVICE_TOKEN", "test-internal-service-token")
    get_settings.cache_clear()
    get_metrics().reset()
    reset_official_account_runtime_state()
    reset_db_session_state()
    Base.metadata.create_all(bind=get_engine())
    yield
    Base.metadata.drop_all(bind=get_engine())
    reset_db_session_state()
    get_metrics().reset()
    reset_official_account_runtime_state()
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


@pytest.fixture
def admin_account_factory(session) -> Callable[..., AdminAccount]:
    def factory(
        *,
        email: str,
        password: str,
        role: AdminRole,
        is_active: bool = True,
        must_change_password: bool = False,
        display_name: str | None = None,
    ) -> AdminAccount:
        account = AdminAccount(
            email=email,
            password_hash=hash_password(password),
            role=role,
            display_name=display_name,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        return account

    return factory


@pytest.fixture
def auth_headers_factory(
    client,
    admin_account_factory,
) -> Callable[..., tuple[dict[str, str], dict]]:
    def factory(
        *,
        email: str,
        password: str,
        role: AdminRole,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> tuple[dict[str, str], dict]:
        admin_account_factory(
            email=email,
            password=password,
            role=role,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200
        payload = response.json()
        return {"Authorization": f"Bearer {payload['access_token']}"}, payload

    return factory


@pytest.fixture
def super_admin_headers(auth_headers_factory) -> dict[str, str]:
    headers, _payload = auth_headers_factory(
        email="super-admin@example.com",
        password="SuperSecret123!",
        role=AdminRole.SUPER_ADMIN,
    )
    return headers


@pytest.fixture
def operator_headers(auth_headers_factory) -> dict[str, str]:
    headers, _payload = auth_headers_factory(
        email="operator@example.com",
        password="OperatorSecret123!",
        role=AdminRole.OPERATOR,
    )
    return headers


@pytest.fixture
def viewer_headers(auth_headers_factory) -> dict[str, str]:
    headers, _payload = auth_headers_factory(
        email="viewer@example.com",
        password="ViewerSecret123!",
        role=AdminRole.VIEWER,
    )
    return headers


@pytest.fixture
def internal_service_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-internal-service-token"}
