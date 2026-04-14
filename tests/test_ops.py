from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    PaperType,
    SignalSource,
    SubscriptionFrequency,
    WorkerRole,
    WorkerStatus,
)
from research_pulse_cn.schemas.paper import PaperProfileCreate, SignalSnapshotCreate
from research_pulse_cn.schemas.subscription_policy import SubscriptionPolicyCreate
from research_pulse_cn.schemas.user import UserProfileCreate
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.heartbeat import WorkerHeartbeatService
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.pulse import PulseService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService
from research_pulse_cn.services.user import UserService


def create_user(client, *, email: str):
    response = client.post(
        "/users",
        json={
            "name": "Ops User",
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


def create_paper(client, *, user_id: str, title: str):
    response = client.post(
        "/papers",
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


def add_signal_pair(client, *, paper_id: str) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (13, 68, 111, newer),
    ):
        response = client.post(
            f"/papers/{paper_id}/signal-snapshots",
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


def create_policy(
    client,
    *,
    user_id: str,
    frequency: SubscriptionFrequency,
    channel: str = "in_app",
    endpoint: str = "console://local",
    policy: dict | None = None,
):
    response = client.post(
        "/subscription-policies",
        json={
            "user_id": user_id,
            "channel": channel,
            "enabled": True,
            "frequency": frequency,
            "frequency_cap": 2,
            "endpoint": endpoint,
            "policy": policy or {},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_scheduler_creates_one_daily_job_per_local_date_and_dedupes(client) -> None:
    user = create_user(client, email="scheduler@example.com")
    now = utcnow()
    daily_policy = create_policy(
        client,
        user_id=user["id"],
        frequency=SubscriptionFrequency.DAILY,
        policy={
            "schedule": {
                "timezone": "UTC",
                "send_hour_local": now.hour,
                "send_minute_local": max(now.minute - 1, 0),
            }
        },
    )

    first = client.post("/ops/scheduler/tick")
    second = client.post("/ops/scheduler/tick")

    assert first.status_code == 200
    assert first.json()["jobs_created"] == 1
    assert first.json()["created_jobs"][0]["subscription_policy_id"] == daily_policy["id"]
    assert first.json()["created_jobs"][0]["schedule_key"].startswith("daily:")
    assert second.status_code == 200
    assert second.json()["jobs_created"] == 0
    assert second.json()["jobs_existing"] == 1

    jobs = client.get("/ops/pulse-jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["scheduled_reason"] == "daily_schedule"
    assert jobs[0]["schedule_key"].startswith("daily:")


def test_event_policies_are_not_auto_scheduled(client) -> None:
    user = create_user(client, email="event-only@example.com")
    create_policy(
        client,
        user_id=user["id"],
        frequency=SubscriptionFrequency.EVENT,
    )

    response = client.post("/ops/scheduler/tick")

    assert response.status_code == 200
    assert response.json()["daily_policies_seen"] == 0
    assert response.json()["jobs_created"] == 0


def test_replay_endpoint_creates_or_reuses_active_replay(client) -> None:
    user = create_user(client, email="replay@example.com")
    paper = create_paper(client, user_id=user["id"], title="Replay paper")
    add_signal_pair(client, paper_id=paper["id"])
    create_policy(client, user_id=user["id"], frequency=SubscriptionFrequency.EVENT)

    run_response = client.post(f"/pulse/run/{user['id']}")
    source_job_id = run_response.json()["job"]["id"]

    first = client.post(f"/ops/pulse-jobs/{source_job_id}/replay")
    second = client.post(f"/ops/pulse-jobs/{source_job_id}/replay")

    assert first.status_code == 200
    assert first.json()["action"] == "replay_created"
    assert first.json()["pulse_job"]["scheduled_reason"] == "replay"
    assert first.json()["pulse_job"]["source_pulse_job_id"] == source_job_id
    assert second.status_code == 200
    assert second.json()["action"] == "existing_active_replay"


def test_requeue_endpoint_moves_dead_letter_delivery_back_to_pending(client, session) -> None:
    user = create_user(client, email="requeue@example.com")
    paper = create_paper(client, user_id=user["id"], title="Requeue paper")
    add_signal_pair(client, paper_id=paper["id"])
    create_policy(
        client,
        user_id=user["id"],
        frequency=SubscriptionFrequency.EVENT,
        channel=ChannelType.DINGTALK.value,
        endpoint="https://fail.example.local/webhook",
    )

    run_response = client.post(f"/pulse/run/{user['id']}")
    delivery_job_id = run_response.json()["delivery_jobs"][0]["id"]
    DeliveryService(session).dispatch_due_jobs()

    redrive = client.post(f"/ops/delivery-jobs/{delivery_job_id}/requeue")

    assert redrive.status_code == 200
    assert redrive.json()["action"] == "requeued"
    assert redrive.json()["status"] == "pending"


def test_worker_heartbeats_are_visible(session, client) -> None:
    WorkerHeartbeatService(session).beat(
        worker_name="test-scheduler",
        worker_role=WorkerRole.SCHEDULER,
        status=WorkerStatus.IDLE,
        metadata={"jobs_created": 1},
        now=utcnow(),
    )

    response = client.get("/ops/heartbeats")

    assert response.status_code == 200
    assert response.json()[0]["worker_name"] == "test-scheduler"
    assert response.json()[0]["metadata"]["jobs_created"] == 1


def test_delivery_attempts_metrics_and_ready_endpoint(client) -> None:
    user = create_user(client, email="ops-metrics@example.com")
    paper = create_paper(client, user_id=user["id"], title="Metrics paper")
    add_signal_pair(client, paper_id=paper["id"])
    create_policy(client, user_id=user["id"], frequency=SubscriptionFrequency.EVENT)

    run_response = client.post(f"/pulse/run/{user['id']}")
    delivery_job_id = run_response.json()["delivery_jobs"][0]["id"]

    attempts = client.get("/ops/delivery-attempts").json()
    metrics = client.get("/ops/metrics")
    ready = client.get("/health/ready")

    assert any(attempt["delivery_job_id"] == delivery_job_id for attempt in attempts)
    assert "pulse_jobs_completed_total" in metrics.text
    assert "delivery_jobs_sent_total" in metrics.text
    assert "pulse_cards_selected_total" in metrics.text
    assert ready.status_code == 200
    assert ready.json()["status"] == "ok"
    assert ready.json()["components"]["database"]["status"] == "ok"


def test_run_endpoint_sets_started_and_completed_timestamps(session) -> None:
    now = utcnow()
    user = UserService(session).create_user(
        UserProfileCreate(
            name="Lifecycle User",
            email="lifecycle@example.com",
            field="Materials",
            interests=["signals"],
            watched_topics=["citations"],
            watched_venues=["JOM"],
            reminder_preferences={"timezone": "UTC"},
            risk_thresholds={"stalled_days": 14},
        )
    )
    paper = PaperService(session).create_paper(
        PaperProfileCreate(
            user_id=user.id,
            title="Lifecycle paper",
            type=PaperType.PUBLISHED,
            stage="published",
            venue="JOM",
            identifiers={},
            source_links=["https://example.local/papers/lifecycle-paper"],
            last_touch_at=now - timedelta(days=7),
            next_action="Review lifecycle status",
            priority=4,
        )
    )
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, now - timedelta(days=1)),
        (13, 68, 111, now - timedelta(hours=1)),
    ):
        PaperService(session).add_signal_snapshot(
            paper.id,
            SignalSnapshotCreate(
                source=SignalSource.GOOGLE_SCHOLAR,
                citation_count=citation_count,
                download_count=download_count,
                read_count=read_count,
                inclusion_status="indexed",
                fetched_at=fetched_at,
            ),
        )
    SubscriptionPolicyService(session).create_policy(
        SubscriptionPolicyCreate(
            user_id=user.id,
            channel=ChannelType.IN_APP,
            enabled=True,
            frequency=SubscriptionFrequency.EVENT,
            frequency_cap=2,
            endpoint="console://local",
            policy={},
        )
    )

    job = PulseService(session).run_now(user.id)

    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.failed_at is None
