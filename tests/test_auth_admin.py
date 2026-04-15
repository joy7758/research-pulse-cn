from datetime import timedelta

from research_pulse_cn.db.models import AuditLog, utcnow
from research_pulse_cn.domain.enums import AdminRole, PaperType, SignalSource, SubscriptionFrequency


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Auth Test User",
            "email": email,
            "field": "Materials",
            "interests": ["signals"],
            "watched_topics": ["citations"],
            "watched_venues": ["JOM"],
            "reminder_preferences": {"timezone": "UTC"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_paper(client, headers, *, user_id: str, title: str) -> dict:
    response = client.post(
        "/papers",
        headers=headers,
        json={
            "user_id": user_id,
            "title": title,
            "type": PaperType.PUBLISHED,
            "stage": "published",
            "venue": "JOM",
            "identifiers": {},
            "source_links": [f"https://example.local/papers/{title.replace(' ', '-').lower()}"],
            "last_touch_at": (utcnow() - timedelta(days=14)).isoformat(),
            "next_action": "Review the latest signal delta",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_signal_pair(client, headers, *, paper_id: str) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (13, 68, 111, newer),
    ):
        response = client.post(
            f"/papers/{paper_id}/signal-snapshots",
            headers=headers,
            json={
                "source": SignalSource.GOOGLE_SCHOLAR,
                "citation_count": citation_count,
                "download_count": download_count,
                "read_count": read_count,
                "inclusion_status": "indexed",
                "fetched_at": fetched_at.isoformat(),
            },
        )
        assert response.status_code == 201


def create_event_policy(client, headers, *, user_id: str) -> None:
    response = client.post(
        "/subscription-policies",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": "in_app",
            "enabled": True,
            "frequency": SubscriptionFrequency.EVENT,
            "frequency_cap": 2,
            "endpoint": "console://local",
            "policy": {},
        },
    )
    assert response.status_code == 201


def test_unauthenticated_access_is_blocked_on_protected_routes(client) -> None:
    assert client.get("/users").status_code == 401
    assert client.get("/ops/metrics").status_code == 401
    assert client.get("/admin/admin-accounts").status_code == 401


def test_health_live_is_public_and_ready_requires_auth(
    client,
    operator_headers,
    internal_service_headers,
) -> None:
    live = client.get("/health/live")
    ready_unauthenticated = client.get("/health/ready")
    ready_operator = client.get("/health/ready", headers=operator_headers)
    ready_service = client.get("/health/ready", headers=internal_service_headers)

    assert live.status_code == 200
    assert ready_unauthenticated.status_code == 401
    assert ready_operator.status_code == 200
    assert ready_service.status_code == 200


def test_admin_login_success_and_failure(client, admin_account_factory, session) -> None:
    admin_account_factory(
        email="operator-login@example.com",
        password="OperatorSecret123!",
        role=AdminRole.OPERATOR,
    )

    failure = client.post(
        "/auth/login",
        json={"email": "operator-login@example.com", "password": "wrong-password"},
    )
    success = client.post(
        "/auth/login",
        json={"email": "operator-login@example.com", "password": "OperatorSecret123!"},
    )
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {success.json()['access_token']}"},
    )
    session.expire_all()

    assert failure.status_code == 401
    assert success.status_code == 200
    assert me.status_code == 200
    assert me.json()["admin"]["role"] == AdminRole.OPERATOR.value
    assert session.query(AuditLog).filter(AuditLog.action == "auth.login_failure").count() == 1
    assert session.query(AuditLog).filter(AuditLog.action == "auth.login_success").count() == 1


def test_inactive_admin_cannot_log_in(client, admin_account_factory) -> None:
    admin_account_factory(
        email="inactive@example.com",
        password="InactiveSecret123!",
        role=AdminRole.VIEWER,
        is_active=False,
    )

    response = client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "InactiveSecret123!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "admin account is inactive"


def test_viewer_can_read_and_preview_but_cannot_write(
    client,
    operator_headers,
    viewer_headers,
) -> None:
    user = create_user(client, operator_headers, email="viewer-target@example.com")

    list_users = client.get("/users", headers=viewer_headers)
    preview = client.post(f"/pulse/preview/{user['id']}", headers=viewer_headers)
    create_attempt = client.post(
        "/users",
        headers=viewer_headers,
        json={
            "name": "Should Fail",
            "email": "viewer-write@example.com",
            "field": "Materials",
            "interests": [],
            "watched_topics": [],
            "watched_venues": [],
            "reminder_preferences": {},
            "risk_thresholds": {},
        },
    )

    assert list_users.status_code == 200
    assert preview.status_code == 200
    assert create_attempt.status_code == 403


def test_operator_can_write_and_run_pulse_but_cannot_manage_admin_accounts(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="operator-target@example.com")
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Operator run paper",
    )
    add_signal_pair(client, operator_headers, paper_id=paper["id"])
    create_event_policy(client, operator_headers, user_id=user["id"])

    run_response = client.post(f"/pulse/run/{user['id']}", headers=operator_headers)
    admin_create = client.post(
        "/admin/admin-accounts",
        headers=operator_headers,
        json={
            "email": "viewer-created@example.com",
            "password": "ViewerSecret123!",
            "role": AdminRole.VIEWER.value,
            "is_active": True,
            "must_change_password": True,
        },
    )

    assert run_response.status_code == 200
    assert admin_create.status_code == 403


def test_super_admin_can_manage_admin_accounts_and_read_audit_logs(
    client,
    super_admin_headers,
) -> None:
    created = client.post(
        "/admin/admin-accounts",
        headers=super_admin_headers,
        json={
            "email": "managed-admin@example.com",
            "password": "ManagedSecret123!",
            "role": AdminRole.VIEWER.value,
            "display_name": "Managed Viewer",
            "is_active": True,
            "must_change_password": True,
        },
    )
    admin_account_id = created.json()["id"]
    updated = client.patch(
        f"/admin/admin-accounts/{admin_account_id}",
        headers=super_admin_headers,
        json={"role": AdminRole.OPERATOR.value, "is_active": True},
    )
    password_reset = client.post(
        f"/admin/admin-accounts/{admin_account_id}/set-password",
        headers=super_admin_headers,
        json={"password": "ManagedReset123!", "must_change_password": False},
    )
    audit_logs = client.get("/admin/audit-logs", headers=super_admin_headers)

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["role"] == AdminRole.OPERATOR.value
    assert password_reset.status_code == 200
    assert password_reset.json()["must_change_password"] is False
    assert audit_logs.status_code == 200
    actions = {entry["action"] for entry in audit_logs.json()}
    assert "admin_account.create" in actions
    assert "admin_account.update" in actions
    assert "admin_account.set_password" in actions


def test_internal_service_token_can_access_ops_but_not_business_crud(
    client,
    internal_service_headers,
) -> None:
    metrics = client.get("/ops/metrics", headers=internal_service_headers)
    ready = client.get("/health/ready", headers=internal_service_headers)
    scheduler_tick = client.post("/ops/scheduler/tick", headers=internal_service_headers)
    create_user_attempt = client.post(
        "/users",
        headers=internal_service_headers,
        json={
            "name": "Service Should Fail",
            "email": "service-blocked@example.com",
            "field": "Materials",
            "interests": [],
            "watched_topics": [],
            "watched_venues": [],
            "reminder_preferences": {},
            "risk_thresholds": {},
        },
    )

    assert metrics.status_code == 200
    assert ready.status_code == 200
    assert scheduler_tick.status_code == 200
    assert create_user_attempt.status_code == 403


def test_refresh_flow_and_logout_revokes_active_session(
    client,
    admin_account_factory,
) -> None:
    admin_account_factory(
        email="refresh@example.com",
        password="RefreshSecret123!",
        role=AdminRole.OPERATOR,
    )

    login = client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "RefreshSecret123!"},
    )
    initial_payload = login.json()
    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": initial_payload["refresh_token"]},
    )
    reused_old_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": initial_payload["refresh_token"]},
    )
    rotated_payload = refresh.json()
    logout = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {rotated_payload['access_token']}"},
        json={"refresh_token": rotated_payload["refresh_token"]},
    )
    reused_rotated_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": rotated_payload["refresh_token"]},
    )

    assert login.status_code == 200
    assert refresh.status_code == 200
    assert reused_old_refresh.status_code == 401
    assert logout.status_code == 200
    assert reused_rotated_refresh.status_code == 401


def test_audit_logs_are_written_for_sensitive_actions(
    client,
    super_admin_headers,
    operator_headers,
) -> None:
    request_headers = {
        **operator_headers,
        "X-Request-ID": "req-user-create-1",
    }
    create_user(client, request_headers, email="audit-target@example.com")

    response = client.get(
        "/admin/audit-logs",
        headers=super_admin_headers,
        params={"action": "user_profile.create"},
    )

    assert response.status_code == 200
    assert response.json()
    assert response.json()[0]["metadata"]["request_id"] == "req-user-create-1"


def test_last_active_super_admin_is_protected(client, super_admin_headers) -> None:
    accounts = client.get("/admin/admin-accounts", headers=super_admin_headers)
    admin_account_id = accounts.json()[0]["id"]

    demote = client.patch(
        f"/admin/admin-accounts/{admin_account_id}",
        headers=super_admin_headers,
        json={"role": AdminRole.OPERATOR.value},
    )
    deactivate = client.patch(
        f"/admin/admin-accounts/{admin_account_id}",
        headers=super_admin_headers,
        json={"is_active": False},
    )

    assert accounts.status_code == 200
    assert len(accounts.json()) == 1
    assert demote.status_code == 409
    assert deactivate.status_code == 409
