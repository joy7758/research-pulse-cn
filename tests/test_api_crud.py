from research_pulse_cn.domain.enums import (
    ChannelType,
    PaperType,
    SignalSource,
    SubscriptionFrequency,
)


def create_user(client, headers):
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Test Researcher",
            "email": "test@example.com",
            "field": "Materials",
            "interests": ["fatigue"],
            "watched_topics": ["heat treatment"],
            "watched_venues": ["TSE"],
            "reminder_preferences": {"timezone": "Asia/Shanghai"},
            "risk_thresholds": {"stalled_days": 14},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_user_and_paper_crud_flow(client, operator_headers) -> None:
    user = create_user(client, operator_headers)

    paper_response = client.post(
        "/papers",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "title": "Fatigue tracking paper",
            "title_zh": "疲劳跟踪论文",
            "type": PaperType.UNDER_REVIEW,
            "stage": "under_review",
            "venue": "TSE",
            "identifiers": {"internal_code": "P-001"},
            "source_links": ["https://example.local/papers/p-001"],
            "last_touch_at": "2026-03-01T00:00:00Z",
            "next_action": "Draft reviewer response",
            "blocker": "Need new chart",
            "priority": 4,
        },
    )
    assert paper_response.status_code == 201
    paper = paper_response.json()

    progress_response = client.post(
        f"/papers/{paper['id']}/progress-events",
        headers=operator_headers,
        json={
            "stage": "revision",
            "happened_at": "2026-03-20T12:00:00Z",
            "summary": "Received reviewer comments and started revision.",
            "evidence_links": ["https://example.local/events/revision"],
            "owner": "editor",
        },
    )
    assert progress_response.status_code == 201

    snapshot_one = client.post(
        f"/papers/{paper['id']}/signal-snapshots",
        headers=operator_headers,
        json={
            "source": SignalSource.MANUAL,
            "citation_count": 4,
            "download_count": 20,
            "read_count": 50,
            "inclusion_status": "indexed",
            "fetched_at": "2026-03-15T00:00:00Z",
        },
    )
    snapshot_two = client.post(
        f"/papers/{paper['id']}/signal-snapshots",
        headers=operator_headers,
        json={
            "source": SignalSource.MANUAL,
            "citation_count": 5,
            "download_count": 28,
            "read_count": 61,
            "inclusion_status": "indexed",
            "fetched_at": "2026-03-25T00:00:00Z",
        },
    )
    assert snapshot_one.status_code == 201
    assert snapshot_two.status_code == 201

    get_paper = client.get(f"/papers/{paper['id']}", headers=operator_headers)
    assert get_paper.status_code == 200
    payload = get_paper.json()
    assert payload["stage"] == "revision"
    assert len(payload["progress_events"]) == 1
    assert len(payload["signal_snapshots"]) == 2

    update_user = client.put(
        f"/users/{user['id']}",
        headers=operator_headers,
        json={"field": "Metallurgy"},
    )
    assert update_user.status_code == 200
    assert update_user.json()["field"] == "Metallurgy"


def test_subscription_policy_crud_flow(client, operator_headers) -> None:
    user = create_user(client, operator_headers)

    created = client.post(
        "/subscription-policies",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel": ChannelType.WEBHOOK,
            "enabled": True,
            "frequency": SubscriptionFrequency.DAILY,
            "endpoint": "https://example.local/webhook",
            "policy": {"digest": True},
        },
    )
    assert created.status_code == 201
    policy_id = created.json()["id"]

    listed = client.get(
        f"/subscription-policies?user_id={user['id']}",
        headers=operator_headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/subscription-policies/{policy_id}",
        headers=operator_headers,
        json={"enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    deleted = client.delete(f"/subscription-policies/{policy_id}", headers=operator_headers)
    assert deleted.status_code == 204
    assert (
        client.get(
            f"/subscription-policies?user_id={user['id']}",
            headers=operator_headers,
        ).json()
        == []
    )
