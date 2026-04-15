from datetime import timedelta

from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    ClientType,
    PaperType,
    SignalSource,
    SubscriptionFrequency,
)


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Sync User",
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
            "last_touch_at": (utcnow() - timedelta(days=10)).isoformat(),
            "next_action": "Check latest signal delta",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_policy(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/subscription-policies",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": "webhook",
            "enabled": True,
            "frequency": SubscriptionFrequency.EVENT.value,
            "frequency_cap": 2,
            "endpoint": "https://hooks.example.local/research-pulse",
            "policy": {"digest": True},
        },
    )
    assert response.status_code == 201
    return response.json()


def add_signal_pair(client, headers, *, paper_id: str) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (14, 71, 120, newer),
    ):
        response = client.post(
            f"/papers/{paper_id}/signal-snapshots",
            headers=headers,
            json={
                "source": SignalSource.GOOGLE_SCHOLAR.value,
                "citation_count": citation_count,
                "download_count": download_count,
                "read_count": read_count,
                "inclusion_status": "indexed",
                "fetched_at": fetched_at.isoformat(),
            },
        )
        assert response.status_code == 201


def create_device(client, operator_headers, *, user_id: str, client_type: str = "desktop") -> dict:
    response = client.post(
        "/admin/client-devices",
        headers=operator_headers,
        json={
            "user_id": user_id,
            "client_type": client_type,
            "display_name": "Primary Desktop",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_operator_can_create_device_and_receive_plaintext_token_once(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="device-create@example.com")

    created = create_device(client, operator_headers, user_id=user["id"])
    listed = client.get("/admin/client-devices", headers=operator_headers)

    assert created["device"]["user_id"] == user["id"]
    assert created["device"]["client_type"] == ClientType.DESKTOP.value
    assert created["plain_text_token"]
    assert "plain_text_token" not in listed.json()[0]


def test_viewer_cannot_create_device(client, operator_headers, viewer_headers) -> None:
    user = create_user(client, operator_headers, email="device-viewer@example.com")

    response = client.post(
        "/admin/client-devices",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "client_type": "desktop",
            "display_name": "Blocked Desktop",
        },
    )

    assert response.status_code == 403


def test_device_token_can_access_sync_but_not_admin_business_or_ops_routes(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="device-authz@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    sync_me = client.get("/sync/me", headers=device_headers)
    admin_route = client.get("/admin/admin-accounts", headers=device_headers)
    business_route = client.get("/users", headers=device_headers)
    ops_route = client.get("/ops/metrics", headers=device_headers)

    assert sync_me.status_code == 200
    assert admin_route.status_code == 401
    assert business_route.status_code == 401
    assert ops_route.status_code == 401


def test_revoked_device_token_is_rejected(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="device-revoke@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}

    revoke = client.post(
        f"/admin/client-devices/{created['device']['id']}/revoke",
        headers=operator_headers,
    )
    sync_me = client.get("/sync/me", headers=device_headers)

    assert revoke.status_code == 200
    assert sync_me.status_code == 401


def test_sync_feed_returns_ordered_events_after_sequence_cursor(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="feed-order@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Feed Ordered Paper")
    client.post(
        f"/papers/{paper['id']}/progress-events",
        headers=operator_headers,
        json={
            "stage": "revision",
            "happened_at": utcnow().isoformat(),
            "summary": "Started revision work.",
            "evidence_links": [],
            "owner": "sync-tester",
        },
    )

    feed = client.get("/sync/feed", headers=device_headers)

    assert feed.status_code == 200
    payload = feed.json()
    sequences = [event["sequence"] for event in payload["events"]]
    assert sequences == sorted(sequences)
    assert sequences[0] >= 1
    assert payload["next_after_sequence"] == sequences[-1]


def test_sync_ack_only_moves_cursor_forward(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="ack-forward@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    create_paper(client, operator_headers, user_id=user["id"], title="Ack Paper")

    feed = client.get("/sync/feed", headers=device_headers)
    last_sequence = feed.json()["next_after_sequence"]
    first_ack = client.post(
        "/sync/ack",
        headers=device_headers,
        json={"last_event_sequence": last_sequence},
    )
    second_ack = client.post("/sync/ack", headers=device_headers, json={"last_event_sequence": 0})

    assert first_ack.status_code == 200
    assert second_ack.status_code == 200
    assert first_ack.json()["last_event_sequence"] == last_sequence
    assert second_ack.json()["last_event_sequence"] == last_sequence


def test_duplicate_client_mutation_id_is_idempotent(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="dup-mutation@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Duplicate Mutation Paper",
    )

    mutation = {
        "client_mutation_id": "paper-patch-1",
        "mutation_type": "paper.patch",
        "resource_type": "paper_profile",
        "resource_id": paper["id"],
        "payload": {"stage": "revision", "priority": 5},
    }
    first = client.post("/sync/push", headers=device_headers, json={"mutations": [mutation]})
    second = client.post("/sync/push", headers=device_headers, json={"mutations": [mutation]})

    assert first.status_code == 200
    assert first.json()["results"][0]["status"] == "applied"
    assert second.status_code == 200
    assert second.json()["results"][0]["status"] == "duplicate"


def test_paper_patch_mutation_is_applied_and_emits_sync_event(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="paper-patch@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Paper Patch")

    push = client.post(
        "/sync/push",
        headers=device_headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": "paper-patch-1",
                    "mutation_type": "paper.patch",
                    "resource_type": "paper_profile",
                    "resource_id": paper["id"],
                    "payload": {"stage": "revision", "next_action": "Prepare response"},
                }
            ]
        },
    )
    updated = client.get(f"/papers/{paper['id']}", headers=operator_headers)
    feed = client.get("/sync/feed", headers=device_headers)

    assert push.status_code == 200
    assert push.json()["results"][0]["status"] == "applied"
    assert updated.json()["stage"] == "revision"
    assert any(
        event["entity_type"] == "paper_profile" and event["entity_id"] == paper["id"]
        for event in feed.json()["events"]
    )


def test_paper_patch_auto_records_work_activity_event(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="paper-work-activity@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Work Activity Paper")

    push = client.post(
        "/sync/push",
        headers=device_headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": "paper-patch-activity-1",
                    "mutation_type": "paper.patch",
                    "resource_type": "paper_profile",
                    "resource_id": paper["id"],
                    "payload": {"stage": "revision", "priority": 5},
                }
            ]
        },
    )
    events = client.get(
        f"/work-activity-events?user_id={user['id']}&activity_type=paper_updated",
        headers=operator_headers,
    )

    assert push.status_code == 200
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["source"] == "sync_mutation"
    assert events.json()[0]["metadata"]["changed_fields"] == ["priority", "stage"]


def test_progress_event_create_mutation_is_applied_and_emits_sync_event(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="progress-mutation@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Progress Mutation")

    push = client.post(
        "/sync/push",
        headers=device_headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": "progress-create-1",
                    "mutation_type": "progress_event.create",
                    "resource_type": "paper_profile",
                    "resource_id": paper["id"],
                    "payload": {
                        "stage": "revision",
                        "happened_at": utcnow().isoformat(),
                        "summary": "Added from desktop client.",
                        "evidence_links": [],
                        "owner": "desktop",
                    },
                }
            ]
        },
    )
    events = client.get(
        f"/papers/{paper['id']}/progress-events",
        headers=operator_headers,
    )
    feed = client.get("/sync/feed", headers=device_headers)

    assert push.status_code == 200
    assert push.json()["results"][0]["status"] == "applied"
    assert len(events.json()) == 1
    assert any(event["entity_type"] == "progress_event" for event in feed.json()["events"])


def test_progress_event_create_auto_records_work_activity_event(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="progress-work-activity@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(
        client,
        operator_headers,
        user_id=user["id"],
        title="Progress Work Activity",
    )

    push = client.post(
        "/sync/push",
        headers=device_headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": "progress-work-activity-1",
                    "mutation_type": "progress_event.create",
                    "resource_type": "paper_profile",
                    "resource_id": paper["id"],
                    "payload": {
                        "stage": "revision",
                        "happened_at": utcnow().isoformat(),
                        "summary": "Added from desktop client.",
                        "evidence_links": [],
                        "owner": "desktop",
                    },
                }
            ]
        },
    )
    events = client.get(
        f"/work-activity-events?user_id={user['id']}&activity_type=progress_event_created",
        headers=operator_headers,
    )

    assert push.status_code == 200
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["source"] == "sync_mutation"
    assert events.json()[0]["metadata"]["stage"] == "revision"


def test_subscription_policy_patch_mutation_is_applied_and_emits_sync_event(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="policy-mutation@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    policy = create_policy(client, operator_headers, user_id=user["id"])

    push = client.post(
        "/sync/push",
        headers=device_headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": "policy-patch-1",
                    "mutation_type": "subscription_policy.patch",
                    "resource_type": "subscription_policy",
                    "resource_id": policy["id"],
                    "payload": {"enabled": False, "frequency_cap": 1},
                }
            ]
        },
    )
    updated = client.get(
        f"/subscription-policies/{policy['id']}",
        headers=operator_headers,
    )
    feed = client.get("/sync/feed", headers=device_headers)

    assert push.status_code == 200
    assert push.json()["results"][0]["status"] == "applied"
    assert updated.json()["enabled"] is False
    assert any(
        event["entity_type"] == "subscription_policy" and event["entity_id"] == policy["id"]
        for event in feed.json()["events"]
    )


def test_subscription_policy_patch_auto_records_work_activity_event(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="policy-work-activity@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    policy = create_policy(client, operator_headers, user_id=user["id"])

    push = client.post(
        "/sync/push",
        headers=device_headers,
        json={
            "mutations": [
                {
                    "client_mutation_id": "policy-work-activity-1",
                    "mutation_type": "subscription_policy.patch",
                    "resource_type": "subscription_policy",
                    "resource_id": policy["id"],
                    "payload": {"enabled": False, "frequency_cap": 1},
                }
            ]
        },
    )
    events = client.get(
        f"/work-activity-events?user_id={user['id']}&activity_type=subscription_policy_updated",
        headers=operator_headers,
    )

    assert push.status_code == 200
    assert events.status_code == 200
    assert len(events.json()) >= 1
    assert any(event["source"] == "sync_mutation" for event in events.json())


def test_work_activity_record_mutation_creates_event_and_is_idempotent(
    client,
    operator_headers,
) -> None:
    user = create_user(client, operator_headers, email="desktop-activity@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Desktop Note Paper")

    mutation = {
        "client_mutation_id": "desktop-activity-1",
        "mutation_type": "work_activity.record",
        "resource_type": "work_activity_event",
        "resource_id": paper["id"],
        "payload": {
            "paper_id": paper["id"],
            "activity_type": "note_saved",
            "summary": "Saved a local note.",
            "metadata": {"note_id": "note-1", "template_kind": "research_note"},
            "happened_at": utcnow().isoformat(),
        },
    }

    first = client.post("/sync/push", headers=device_headers, json={"mutations": [mutation]})
    second = client.post("/sync/push", headers=device_headers, json={"mutations": [mutation]})
    events = client.get(
        f"/work-activity-events?user_id={user['id']}&activity_type=note_saved",
        headers=operator_headers,
    )

    assert first.status_code == 200
    assert first.json()["results"][0]["status"] == "applied"
    assert first.json()["results"][0]["resulting_event_sequence"] is None
    assert second.status_code == 200
    assert second.json()["results"][0]["status"] == "duplicate"
    assert len(events.json()) == 1
    assert events.json()[0]["source"] == "desktop_local"


def test_server_side_crud_and_pulse_actions_emit_sync_events(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="server-events@example.com")
    created = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created['plain_text_token']}"}
    paper = create_paper(client, operator_headers, user_id=user["id"], title="Server Event Paper")
    client.put(
        f"/papers/{paper['id']}",
        headers=operator_headers,
        json={"stage": "revision", "priority": 5},
    )
    client.post(
        f"/papers/{paper['id']}/progress-events",
        headers=operator_headers,
        json={
            "stage": "revision",
            "happened_at": utcnow().isoformat(),
            "summary": "Server-side progress event.",
            "evidence_links": [],
            "owner": "operator",
        },
    )
    add_signal_pair(client, operator_headers, paper_id=paper["id"])
    create_policy(client, operator_headers, user_id=user["id"])
    client.post(f"/pulse/run/{user['id']}", headers=operator_headers)

    feed = client.get("/sync/feed", headers=device_headers)

    assert feed.status_code == 200
    entity_types = {event["entity_type"] for event in feed.json()["events"]}
    assert "paper_profile" in entity_types
    assert "progress_event" in entity_types
    assert "signal_snapshot" in entity_types
    assert "subscription_policy" in entity_types
    assert "pulse_card" in entity_types
    assert "pulse_digest_issue" in entity_types

    digest_event = next(
        event for event in feed.json()["events"] if event["entity_type"] == "pulse_digest_issue"
    )
    assert digest_event["payload"]["highlights"]
    assert digest_event["payload"]["items"]
