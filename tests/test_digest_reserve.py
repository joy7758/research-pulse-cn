import hashlib
from datetime import timedelta
from uuid import UUID

import httpx

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.db.models import PaperProfile, PulseCard, PulseJob, utcnow
from research_pulse_cn.domain.enums import (
    OfficialAccountProviderMode,
    PaperType,
    PulseCardType,
    PulseJobScheduledReason,
    PulseJobStatus,
    SignalSource,
    SubscriptionFrequency,
    WeChatBindingChannelType,
    WeChatBindingState,
)


def create_user(client, headers, *, email: str) -> dict:
    response = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Digest User",
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
            "type": PaperType.PUBLISHED.value,
            "stage": "published",
            "venue": "JOM",
            "identifiers": {},
            "source_links": [f"https://example.local/{title.lower().replace(' ', '-')}"],
            "last_touch_at": (utcnow() - timedelta(days=14)).isoformat(),
            "next_action": "Review the latest signal delta",
            "priority": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_signal_pair(client, headers, *, paper_id: str, latest_delta: int = 4) -> None:
    older = utcnow() - timedelta(days=1)
    newer = utcnow() - timedelta(hours=1)
    for citation_count, download_count, read_count, fetched_at in (
        (10, 50, 80, older),
        (10 + latest_delta, 60 + latest_delta, 90 + latest_delta, newer),
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


def create_policy(client, headers, *, user_id: str) -> None:
    response = client.post(
        "/subscription-policies",
        headers=headers,
        json={
            "user_id": user_id,
            "channel": "webhook",
            "enabled": True,
            "frequency": SubscriptionFrequency.EVENT.value,
            "frequency_cap": 3,
            "endpoint": "https://hooks.example.local/research-pulse",
            "policy": {"digest": True},
        },
    )
    assert response.status_code == 201


def create_device(client, headers, *, user_id: str) -> dict:
    response = client.post(
        "/admin/client-devices",
        headers=headers,
        json={
            "user_id": user_id,
            "client_type": "desktop",
            "display_name": "Digest Desktop",
        },
    )
    assert response.status_code == 201
    return response.json()


def seed_sectioned_digest_cards(session, *, user_id: str) -> dict[str, str]:
    user_uuid = UUID(user_id)
    scheduled_for = utcnow()
    linked_paper = PaperProfile(
        user_id=user_uuid,
        title="Digest Focus Paper",
        type=PaperType.REVISION,
        stage="revision",
        venue="JOM",
        identifiers={},
        source_links=["https://example.local/digest-focus-paper"],
        last_touch_at=scheduled_for - timedelta(days=2),
        next_action="Finish the response appendix",
        blocker=None,
        priority=5,
    )
    session.add(linked_paper)
    session.flush()

    pulse_job = PulseJob(
        user_id=user_uuid,
        scheduled_for=scheduled_for,
        scheduled_reason=PulseJobScheduledReason.MANUAL_RUN,
        status=PulseJobStatus.COMPLETED,
        started_at=scheduled_for,
        completed_at=scheduled_for,
    )
    session.add(pulse_job)
    session.flush()

    cards = [
        PulseCard(
            pulse_job_id=pulse_job.id,
            user_id=user_uuid,
            source_paper_id=linked_paper.id,
            card_type=PulseCardType.TODAY_SUGGESTION,
            priority=1,
            score_total=20,
            score_breakdown={"base_weight": 6, "total": 20},
            title="Execute next action for Digest Focus Paper",
            summary="Finish the response appendix.",
            why_now="This paper already has the clearest next step for today.",
            action_text="Finish the response appendix",
            deep_link=f"/papers/{linked_paper.id}",
            candidate_metadata={"suggestion_kind": "execute_next_action"},
            generated_by={"provider": "dummy-model-provider", "mode": "deterministic"},
            generated_at=scheduled_for,
        ),
        PulseCard(
            pulse_job_id=pulse_job.id,
            user_id=user_uuid,
            source_paper_id=None,
            card_type=PulseCardType.YESTERDAY_SUMMARY,
            priority=2,
            score_total=12,
            score_breakdown={"base_weight": 10, "total": 12},
            title="Yesterday summary for 2026-04-14",
            summary="Yesterday recorded 2 work activities.",
            why_now="A concise recap keeps the current work context visible.",
            action_text=None,
            deep_link="/pulse/input-preview/example-user",
            candidate_metadata={"summary_date": "2026-04-14"},
            generated_by={"provider": "dummy-model-provider", "mode": "deterministic"},
            generated_at=scheduled_for + timedelta(minutes=1),
        ),
        PulseCard(
            pulse_job_id=pulse_job.id,
            user_id=user_uuid,
            source_paper_id=linked_paper.id,
            card_type=PulseCardType.SIGNAL_CHANGE,
            priority=3,
            score_total=11,
            score_breakdown={"base_weight": 8, "total": 11},
            title="Signal update for Digest Focus Paper",
            summary="Citation and read counts moved this week.",
            why_now="The latest signal snapshot changed enough to deserve a check.",
            action_text="Review signal update",
            deep_link=f"/papers/{linked_paper.id}",
            candidate_metadata={"signal_source": "google_scholar"},
            generated_by={"provider": "dummy-model-provider", "mode": "deterministic"},
            generated_at=scheduled_for + timedelta(minutes=2),
        ),
        PulseCard(
            pulse_job_id=pulse_job.id,
            user_id=user_uuid,
            source_paper_id=linked_paper.id,
            card_type=PulseCardType.RELATED_PAPER,
            priority=4,
            score_total=13,
            score_breakdown={"base_weight": 4, "total": 13},
            title="Related paper: Diffusion Response Paper",
            summary="Diffusion Response Paper appeared in Acta Materialia (2024).",
            why_now=(
                "A recent normalized related-paper result matches the current revision context."
            ),
            action_text="Review related paper",
            deep_link="https://example.org/related-paper",
            external_reference_key="doi:10.1234/diffusion-response-paper",
            candidate_metadata={"external_reference_key": "doi:10.1234/diffusion-response-paper"},
            generated_by={"provider": "dummy-model-provider", "mode": "deterministic"},
            generated_at=scheduled_for + timedelta(minutes=3),
        ),
        PulseCard(
            pulse_job_id=pulse_job.id,
            user_id=user_uuid,
            source_paper_id=linked_paper.id,
            card_type=PulseCardType.NEXT_ACTION,
            priority=5,
            score_total=9,
            score_breakdown={"base_weight": 8, "total": 9},
            title="Next action for Digest Focus Paper",
            summary="Review the remaining figure notes.",
            why_now="This paper still has another actionable follow-up.",
            action_text="Review figure notes",
            deep_link=f"/papers/{linked_paper.id}",
            candidate_metadata={"next_action": "Review the remaining figure notes."},
            generated_by={"provider": "dummy-model-provider", "mode": "deterministic"},
            generated_at=scheduled_for + timedelta(minutes=4),
        ),
    ]
    session.add_all(cards)
    session.commit()
    return {
        "pulse_job_id": str(pulse_job.id),
        "issue_date": scheduled_for.date().isoformat(),
        "paper_id": str(linked_paper.id),
    }


def create_digest_ready_user(client, headers, *, email: str) -> tuple[dict, dict]:
    user = create_user(client, headers, email=email)
    paper = create_paper(client, headers, user_id=user["id"], title="Digest Ranking Paper")
    add_signal_pair(client, headers, paper_id=paper["id"])
    create_policy(client, headers, user_id=user["id"])
    run_response = client.post(f"/pulse/run/{user['id']}", headers=headers)
    assert run_response.status_code == 200
    return user, run_response.json()


def configure_official_account_settings(
    monkeypatch,
    *,
    provider_mode: str,
    callback_enabled: bool = False,
    real_send_enabled: bool = False,
    app_id: str | None = "wx-official-app",
    app_secret: str | None = "test-official-secret",
    callback_token: str = "callback-token",
    callback_aes_key: str = "callback-aes-key",
    template_id: str | None = "digest-template-001",
    article_base_url: str = "https://digest.example.local",
    mini_program_app_id: str = "wx-mini-app",
    transport_kind: str = "template_notice",
    access_token_refresh_skew_seconds: int = 120,
    connect_timeout_seconds: int = 5,
    read_timeout_seconds: int = 10,
    max_retries: int = 2,
    template_field_mapping_json: str | None = None,
) -> None:
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_PROVIDER_MODE", provider_mode)
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND", transport_kind)
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED",
        "true" if real_send_enabled else "false",
    )
    if app_id is None:
        monkeypatch.delenv("APP_WECHAT_OFFICIAL_APP_ID", raising=False)
    else:
        monkeypatch.setenv("APP_WECHAT_OFFICIAL_APP_ID", app_id)
    if app_secret is None:
        monkeypatch.delenv("APP_WECHAT_OFFICIAL_APP_SECRET", raising=False)
    else:
        monkeypatch.setenv("APP_WECHAT_OFFICIAL_APP_SECRET", app_secret)
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_CALLBACK_TOKEN", callback_token)
    monkeypatch.setenv("APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY", callback_aes_key)
    if template_id is None:
        monkeypatch.delenv("APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID", raising=False)
    else:
        monkeypatch.setenv("APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID", template_id)
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED",
        "true" if callback_enabled else "false",
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID",
        mini_program_app_id,
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL",
        article_base_url,
    )
    if template_field_mapping_json is None:
        monkeypatch.delenv("APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON", raising=False)
    else:
        monkeypatch.setenv(
            "APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON",
            template_field_mapping_json,
        )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_ACCESS_TOKEN_REFRESH_SKEW_SECONDS",
        str(access_token_refresh_skew_seconds),
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_HTTP_CONNECT_TIMEOUT_SECONDS",
        str(connect_timeout_seconds),
    )
    monkeypatch.setenv(
        "APP_OFFICIAL_ACCOUNT_HTTP_READ_TIMEOUT_SECONDS",
        str(read_timeout_seconds),
    )
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_MAX_RETRIES", str(max_retries))
    monkeypatch.setenv("APP_OFFICIAL_ACCOUNT_DISPATCH_TIMEOUT_SECONDS", "7")
    get_settings.cache_clear()


def install_mock_official_account_http(
    monkeypatch,
    *,
    token_payload: dict | None = None,
    send_payload: dict | None = None,
    send_status_code: int = 200,
) -> dict[str, int]:
    calls = {"token": 0, "send": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/cgi-bin/token"):
            calls["token"] += 1
            return httpx.Response(
                200,
                json=token_payload or {"access_token": "test-access-token", "expires_in": 7200},
            )
        if request.url.path.endswith("/cgi-bin/message/template/send"):
            calls["send"] += 1
            return httpx.Response(
                send_status_code,
                json=send_payload or {"errcode": 0, "errmsg": "ok", "msgid": 12345},
            )
        raise AssertionError(
            f"unexpected official-account HTTP request: {request.method} {request.url}"
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "research_pulse_cn.services.official_account.create_official_account_http_client",
        lambda _settings: httpx.Client(transport=transport),
    )
    return calls


def build_callback_signature(token: str, timestamp: str, nonce: str) -> str:
    return hashlib.sha1("".join(sorted([token, timestamp, nonce])).encode("utf-8")).hexdigest()


def build_official_account_event_xml(
    *,
    openid: str,
    event: str,
    to_user_name: str = "gh_test_official",
    event_time: int = 1_710_000_000,
    event_key: str | None = None,
) -> str:
    event_key_node = "" if event_key is None else f"<EventKey><![CDATA[{event_key}]]></EventKey>"
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user_name}]]></ToUserName>"
        f"<FromUserName><![CDATA[{openid}]]></FromUserName>"
        f"<CreateTime>{event_time}</CreateTime>"
        "<MsgType><![CDATA[event]]></MsgType>"
        f"<Event><![CDATA[{event}]]></Event>"
        f"{event_key_node}"
        "</xml>"
    )


def test_operator_can_create_and_update_wechat_bindings(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="binding-operator@example.com")

    created = client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "openid-001",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
            "display_label": "Primary OA",
            "metadata": {"note": "manual bind"},
        },
    )
    binding_id = created.json()["id"]
    updated = client.patch(
        f"/admin/wechat-bindings/{binding_id}",
        headers=operator_headers,
        json={
            "digest_enabled": False,
            "display_label": "Primary OA Updated",
            "metadata": {"note": "updated"},
        },
    )

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["digest_enabled"] is False
    assert updated.json()["display_label"] == "Primary OA Updated"


def test_viewer_cannot_manage_wechat_bindings(client, operator_headers, viewer_headers) -> None:
    user = create_user(client, operator_headers, email="binding-viewer@example.com")

    response = client.post(
        "/admin/wechat-bindings",
        headers=viewer_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "openid-002",
        },
    )

    assert response.status_code == 403


def test_manual_digest_build_is_idempotent_per_user_and_date(client, operator_headers) -> None:
    user, run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-idempotent@example.com",
    )
    issues = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    assert issues.status_code == 200
    issue = issues.json()[0]

    first_build = client.post(
        f"/admin/digest-issues/build/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": issue["issue_date"],
            "source_pulse_job_id": run_payload["job"]["id"],
        },
    )
    second_build = client.post(
        f"/admin/digest-issues/build/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": issue["issue_date"],
            "source_pulse_job_id": run_payload["job"]["id"],
        },
    )
    issues_after = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"], "issue_date": issue["issue_date"]},
    )

    assert first_build.status_code == 200
    assert second_build.status_code == 200
    assert first_build.json()["issue"]["id"] == issue["id"]
    assert second_build.json()["issue"]["id"] == issue["id"]
    assert len(issues_after.json()) == 1


def test_daily_pulse_completion_auto_upserts_digest_issue(client, operator_headers) -> None:
    user, run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-auto@example.com",
    )

    issues = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )

    assert issues.status_code == 200
    assert len(issues.json()) == 1
    assert issues.json()[0]["source_pulse_job_id"] == run_payload["job"]["id"]
    assert issues.json()[0]["status"] == "ready"


def test_digest_items_preserve_stable_order_from_selected_cards(client, operator_headers) -> None:
    user, run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-order@example.com",
    )
    issues = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )
    digest_issue_id = issues.json()[0]["id"]

    detail = client.get(f"/admin/digest-issues/{digest_issue_id}", headers=operator_headers)

    assert detail.status_code == 200
    assert [item["pulse_card_id"] for item in detail.json()["items"]] == [
        card["id"] for card in run_payload["cards"]
    ]


def test_digest_orchestration_builds_stable_sections_from_selected_cards(
    client,
    operator_headers,
    session,
) -> None:
    user = create_user(client, operator_headers, email="digest-orchestrate@example.com")
    seeded = seed_sectioned_digest_cards(session, user_id=user["id"])

    orchestrated = client.post(
        f"/admin/digest-issues/orchestrate/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": seeded["issue_date"],
            "source_pulse_job_id": seeded["pulse_job_id"],
        },
    )

    assert orchestrated.status_code == 200
    payload = orchestrated.json()["issue"]["content_payload"]
    assert payload["section_order"] == [
        "today_focus",
        "yesterday_recap",
        "signal_updates",
        "related_papers",
        "other_updates",
    ]
    sections = {section["kind"]: section for section in payload["sections"]}
    assert sections["today_focus"]["items"][0]["card_type"] == "today_suggestion"
    assert sections["yesterday_recap"]["items"][0]["card_type"] == "yesterday_summary"
    assert sections["related_papers"]["items"][0]["card_type"] == "related_paper"
    all_ids = [
        item["pulse_card_id"] for section in payload["sections"] for item in section["items"]
    ]
    assert len(all_ids) == len(set(all_ids))
    assert payload["focus_card"]["card_type"] == "today_suggestion"


def test_daily_preview_returns_publication_preview_and_handles_null_source_paper(
    client,
    operator_headers,
    session,
) -> None:
    user = create_user(client, operator_headers, email="digest-preview@example.com")
    seeded = seed_sectioned_digest_cards(session, user_id=user["id"])
    issue = client.post(
        f"/admin/digest-issues/orchestrate/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": seeded["issue_date"],
            "source_pulse_job_id": seeded["pulse_job_id"],
        },
    ).json()["issue"]

    preview = client.get(
        f"/admin/digest-issues/{issue['id']}/daily-preview",
        headers=operator_headers,
    )

    assert preview.status_code == 200
    payload = preview.json()["content_payload"]
    assert payload["publication_preview"]["digest_title"] == issue["title"]
    assert payload["publication_preview"]["primary_cta_path"] == issue["deep_link_path"]
    recap_item = next(
        item for item in payload["sections"][1]["items"] if item["card_type"] == "yesterday_summary"
    )
    assert recap_item["source_paper_id"] is None


def test_auto_prepare_flag_prepares_publication_without_dispatching_real_send(
    client,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DRY_RUN.value,
    )
    monkeypatch.setenv("APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT", "true")
    get_settings.cache_clear()

    user = create_user(client, operator_headers, email="digest-auto-prepare@example.com")
    seeded = seed_sectioned_digest_cards(session, user_id=user["id"])
    binding = client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "auto-prepare-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    assert binding.status_code == 201

    orchestrated = client.post(
        f"/admin/digest-issues/orchestrate/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": seeded["issue_date"],
            "source_pulse_job_id": seeded["pulse_job_id"],
        },
    )

    assert orchestrated.status_code == 200
    jobs = orchestrated.json()["publication_jobs"]
    assert len(jobs) == 1
    assert jobs[0]["status"] == "prepared"
    attempts = client.get(
        "/admin/digest-publication-attempts",
        headers=operator_headers,
        params={"issue_date": seeded["issue_date"]},
    )
    assert attempts.status_code == 200
    assert attempts.json() == []


def test_prepare_publication_only_uses_eligible_official_account_bindings(
    client,
    operator_headers,
) -> None:
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-prepare@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]

    binding_payloads = [
        {
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "eligible-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
        {
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "not-subscribed",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": False,
            "digest_enabled": True,
        },
        {
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "revoked-openid",
            "bind_state": WeChatBindingState.REVOKED.value,
            "subscribed": True,
            "digest_enabled": True,
        },
        {
            "channel_type": WeChatBindingChannelType.MINI_PROGRAM.value,
            "app_id": "wx-mini-app",
            "openid": "mini-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    ]
    for payload in binding_payloads:
        response = client.post(
            "/admin/wechat-bindings",
            headers=operator_headers,
            json={"user_id": user["id"], **payload},
        )
        assert response.status_code == 201

    prepared = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    )

    assert prepared.status_code == 200
    assert len(prepared.json()["publication_jobs"]) == 1
    job = prepared.json()["publication_jobs"][0]
    assert job["status"] == "prepared"
    assert job["publish_target"] == "official_account"
    assert job["provider_name"] == "official_account_boundary"
    assert job["external_message_id"] is None
    assert job["payload"]["binding"]["openid"] == "eligible-openid"


def test_prepare_publication_prefers_publication_preview_when_present(
    client,
    operator_headers,
    session,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DRY_RUN.value,
    )
    user = create_user(client, operator_headers, email="digest-publication-preview@example.com")
    seeded = seed_sectioned_digest_cards(session, user_id=user["id"])
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "preview-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    issue = client.post(
        f"/admin/digest-issues/orchestrate/{user['id']}",
        headers=operator_headers,
        json={
            "issue_date": seeded["issue_date"],
            "source_pulse_job_id": seeded["pulse_job_id"],
        },
    ).json()["issue"]

    prepared = client.post(
        f"/admin/digest-issues/{issue['id']}/prepare-publication",
        headers=operator_headers,
    )

    assert prepared.status_code == 200
    publication_job = prepared.json()["publication_jobs"][0]
    assert (
        publication_job["payload"]["title"]
        == issue["content_payload"]["publication_preview"]["digest_title"]
    )
    assert (
        publication_job["payload"]["summary"]
        == issue["content_payload"]["publication_preview"]["digest_subtitle"]
    )
    assert (
        publication_job["payload"]["landing"]["deep_link_path"]
        == issue["content_payload"]["publication_preview"]["primary_cta_path"]
    )


def test_digest_metrics_appear_on_ops_metrics(client, operator_headers) -> None:
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-metrics@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "metrics-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    )

    metrics = client.get("/ops/metrics", headers=operator_headers)

    assert metrics.status_code == 200
    assert "digest_issues_built_total" in metrics.text
    assert "digest_publication_jobs_prepared_total" in metrics.text
    assert "digest_publication_jobs_failed_total" in metrics.text


def test_digest_issue_sync_event_is_emitted(client, operator_headers) -> None:
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-sync@example.com",
    )
    created_device = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created_device['plain_text_token']}"}

    feed = client.get("/sync/feed", headers=device_headers)

    assert feed.status_code == 200
    assert any(event["entity_type"] == "pulse_digest_issue" for event in feed.json()["events"])


def test_device_token_cannot_access_digest_admin_routes(client, operator_headers) -> None:
    user = create_user(client, operator_headers, email="digest-device-block@example.com")
    created_device = create_device(client, operator_headers, user_id=user["id"])
    device_headers = {"Authorization": f"Bearer {created_device['plain_text_token']}"}

    response = client.get("/admin/digest-issues", headers=device_headers)

    assert response.status_code == 401


def test_operator_can_dispatch_publication_job_in_dry_run_mode(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DRY_RUN.value,
    )
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    prepared = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()
    publication_job = prepared["publication_jobs"][0]

    dispatched = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )
    attempts = client.get(
        "/admin/digest-publication-attempts",
        headers=operator_headers,
        params={"publication_job_id": publication_job["id"]},
    )

    assert dispatched.status_code == 200
    assert dispatched.json()["action"] == "previewed"
    assert dispatched.json()["publication_job"]["status"] == "previewed"
    assert dispatched.json()["publication_job"]["external_message_id"] is None
    assert dispatched.json()["attempt"]["status"] == "previewed"
    assert dispatched.json()["attempt"]["provider_mode"] == "dry_run"
    assert attempts.status_code == 200
    assert len(attempts.json()) == 1


def test_viewer_cannot_dispatch_publication_job(
    client,
    operator_headers,
    viewer_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DRY_RUN.value,
    )
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch-viewer@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-viewer-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    response = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=viewer_headers,
    )

    assert response.status_code == 403


def test_disabled_provider_mode_blocks_dispatch_cleanly(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DISABLED.value,
    )
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch-disabled@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-disabled-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    dispatched = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )
    attempts = client.get(
        "/admin/digest-publication-attempts",
        headers=operator_headers,
        params={"publication_job_id": publication_job["id"]},
    )

    assert dispatched.status_code == 409
    assert "disabled" in dispatched.json()["detail"]
    assert attempts.status_code == 200
    assert attempts.json()[0]["status"] == "failed"


def test_provider_status_endpoint_reflects_mode_without_leaking_secrets(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DRY_RUN.value,
        callback_enabled=True,
    )

    response = client.get("/admin/official-account/provider-status", headers=operator_headers)

    assert response.status_code == 200
    assert response.json()["mode"] == "dry_run"
    assert response.json()["transport_kind"] == "template_notice"
    assert response.json()["readiness"] is True
    assert response.json()["callback_enabled"] is True
    assert response.json()["has_app_secret"] is True
    assert response.json()["has_digest_template_id"] is True
    assert response.json()["token_cached"] is False
    assert response.json()["cache_backend"] == "in_memory"
    assert "test-official-secret" not in response.text


def test_provider_status_readiness_is_false_in_real_mode_when_required_settings_missing(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
        app_secret=None,
        template_id=None,
    )

    response = client.get("/admin/official-account/provider-status", headers=operator_headers)

    assert response.status_code == 200
    assert response.json()["mode"] == "real"
    assert response.json()["readiness"] is False
    assert "wechat official app secret is missing" in response.json()["readiness_failures"]
    assert "official-account digest template id is missing" in response.json()["readiness_failures"]


def test_manual_provider_token_refresh_in_real_mode_updates_cache_state(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
    )
    install_mock_official_account_http(monkeypatch)

    response = client.post(
        "/admin/official-account/provider-token/refresh",
        headers=operator_headers,
    )
    provider_status = client.get(
        "/admin/official-account/provider-status",
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["action"] == "refreshed"
    assert response.json()["mode"] == "real"
    assert response.json()["token_cached"] is True
    assert response.json()["token_expires_at"] is not None
    assert response.json()["last_refresh_at"] is not None
    assert provider_status.json()["token_cached"] is True
    assert "test-access-token" not in provider_status.text


def test_repeated_token_fetch_within_ttl_uses_cache_and_avoids_duplicate_http_fetch(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
    )
    calls = install_mock_official_account_http(monkeypatch)

    refreshed = client.post(
        "/admin/official-account/provider-token/refresh",
        headers=operator_headers,
    )
    assert refreshed.status_code == 200
    assert calls["token"] == 1

    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-real-cache@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-real-cache-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    dispatched = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )

    assert dispatched.status_code == 200
    assert calls["token"] == 1
    assert calls["send"] == 1


def test_operator_can_dispatch_publication_job_in_real_mode_with_mocked_http(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
    )
    install_mock_official_account_http(monkeypatch)
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch-real@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-real-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    dispatched = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )

    assert dispatched.status_code == 200
    assert dispatched.json()["action"] == "sent"
    assert dispatched.json()["publication_job"]["status"] == "sent"
    assert dispatched.json()["publication_job"]["external_message_id"] == "12345"
    assert dispatched.json()["attempt"]["status"] == "sent"
    assert dispatched.json()["attempt"]["provider_mode"] == "real"


def test_real_send_success_marks_publication_job_as_sent_and_records_attempt(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
    )
    install_mock_official_account_http(monkeypatch)
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch-real-success@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-real-success-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )
    refreshed_job = client.get(
        "/admin/digest-publication-jobs",
        headers=operator_headers,
        params={"digest_issue_id": digest_issue["id"], "status": "sent"},
    )
    attempts = client.get(
        "/admin/digest-publication-attempts",
        headers=operator_headers,
        params={"publication_job_id": publication_job["id"]},
    )

    assert refreshed_job.status_code == 200
    assert len(refreshed_job.json()) == 1
    assert refreshed_job.json()[0]["published_at"] is not None
    assert attempts.json()[0]["external_message_id"] == "12345"
    assert attempts.json()[0]["provider_response_code"] == "0"


def test_real_send_failure_marks_publication_job_failed_and_records_error_details(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
    )
    install_mock_official_account_http(
        monkeypatch,
        send_payload={"errcode": 40003, "errmsg": "invalid openid"},
    )
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch-real-failure@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-real-failure-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    dispatched = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )

    assert dispatched.status_code == 200
    assert dispatched.json()["action"] == "failed"
    assert dispatched.json()["publication_job"]["status"] == "failed"
    assert dispatched.json()["publication_job"]["last_error"] == "invalid openid"
    assert dispatched.json()["attempt"]["status"] == "failed"
    assert dispatched.json()["attempt"]["provider_response_code"] == "40003"
    assert dispatched.json()["attempt"]["provider_response_message"] == "invalid openid"


def test_already_sent_publication_job_is_not_redispatched_by_default(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.REAL.value,
        real_send_enabled=True,
    )
    calls = install_mock_official_account_http(monkeypatch)
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="digest-dispatch-real-repeat@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "dispatch-real-repeat-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]

    first = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )
    second = client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )
    attempts = client.get(
        "/admin/digest-publication-attempts",
        headers=operator_headers,
        params={"publication_job_id": publication_job["id"]},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["action"] == "already_sent"
    assert len(attempts.json()) == 1
    assert calls["send"] == 1


def test_callback_verification_path_behaves_correctly_when_enabled(
    client,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DISABLED.value,
        callback_enabled=True,
    )
    timestamp = "1710000000"
    nonce = "nonce-001"
    echostr = "hello-wechat"
    signature = build_callback_signature("callback-token", timestamp, nonce)

    response = client.get(
        "/integrations/wechat/official-account/callback",
        params={
            "signature": signature,
            "timestamp": timestamp,
            "nonce": nonce,
            "echostr": echostr,
        },
    )

    assert response.status_code == 200
    assert response.text == echostr


def test_callback_subscribe_updates_matching_binding(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DISABLED.value,
        callback_enabled=True,
    )
    user = create_user(client, operator_headers, email="callback-subscribe@example.com")
    binding = client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "subscribe-openid",
            "bind_state": WeChatBindingState.PENDING.value,
            "subscribed": False,
            "digest_enabled": True,
        },
    ).json()
    timestamp = "1710000001"
    nonce = "nonce-002"
    payload = build_official_account_event_xml(openid="subscribe-openid", event="subscribe")
    signature = build_callback_signature("callback-token", timestamp, nonce)

    response = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=payload,
        headers={"Content-Type": "application/xml"},
    )
    updated_binding = client.get(
        "/admin/wechat-bindings",
        headers=operator_headers,
        params={"user_id": user["id"], "channel_type": "official_account"},
    ).json()[0]

    assert binding["id"] == updated_binding["id"]
    assert response.status_code == 200
    assert updated_binding["subscribed"] is True
    assert updated_binding["bind_state"] == "active"
    assert updated_binding["subscribed_at"] is not None


def test_callback_unsubscribe_updates_matching_binding(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DISABLED.value,
        callback_enabled=True,
    )
    user = create_user(client, operator_headers, email="callback-unsubscribe@example.com")
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "unsubscribe-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    timestamp = "1710000002"
    nonce = "nonce-003"
    payload = build_official_account_event_xml(openid="unsubscribe-openid", event="unsubscribe")
    signature = build_callback_signature("callback-token", timestamp, nonce)

    response = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=payload,
        headers={"Content-Type": "application/xml"},
    )
    updated_binding = client.get(
        "/admin/wechat-bindings",
        headers=operator_headers,
        params={"user_id": user["id"], "channel_type": "official_account"},
    ).json()[0]

    assert response.status_code == 200
    assert updated_binding["subscribed"] is False
    assert updated_binding["unsubscribed_at"] is not None


def test_duplicate_callbacks_are_deduped(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DISABLED.value,
        callback_enabled=True,
    )
    user = create_user(client, operator_headers, email="callback-duplicate@example.com")
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "duplicate-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": False,
            "digest_enabled": True,
        },
    )
    timestamp = "1710000003"
    nonce = "nonce-004"
    payload = build_official_account_event_xml(openid="duplicate-openid", event="subscribe")
    signature = build_callback_signature("callback-token", timestamp, nonce)

    first = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=payload,
        headers={"Content-Type": "application/xml"},
    )
    second = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=payload,
        headers={"Content-Type": "application/xml"},
    )
    events = client.get(
        "/admin/official-account/callback-events",
        headers=operator_headers,
        params={"user_id": user["id"]},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["processing_status"] == "duplicate"


def test_unknown_openid_callback_does_not_auto_create_binding(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DISABLED.value,
        callback_enabled=True,
    )
    timestamp = "1710000004"
    nonce = "nonce-005"
    payload = build_official_account_event_xml(openid="unknown-openid", event="subscribe")
    signature = build_callback_signature("callback-token", timestamp, nonce)

    response = client.post(
        "/integrations/wechat/official-account/callback",
        params={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        content=payload,
        headers={"Content-Type": "application/xml"},
    )
    events = client.get(
        "/admin/official-account/callback-events",
        headers=operator_headers,
    )
    bindings = client.get(
        "/admin/wechat-bindings",
        headers=operator_headers,
        params={"channel_type": "official_account"},
    )

    assert response.status_code == 200
    assert len(bindings.json()) == 0
    assert events.json()[0]["linked_binding_id"] is None


def test_official_account_metrics_appear_on_ops_metrics(
    client,
    operator_headers,
    monkeypatch,
) -> None:
    configure_official_account_settings(
        monkeypatch,
        provider_mode=OfficialAccountProviderMode.DRY_RUN.value,
        callback_enabled=True,
    )
    user, _run_payload = create_digest_ready_user(
        client,
        operator_headers,
        email="official-account-metrics@example.com",
    )
    digest_issue = client.get(
        "/admin/digest-issues",
        headers=operator_headers,
        params={"user_id": user["id"]},
    ).json()[0]
    client.post(
        "/admin/wechat-bindings",
        headers=operator_headers,
        json={
            "user_id": user["id"],
            "channel_type": WeChatBindingChannelType.OFFICIAL_ACCOUNT.value,
            "app_id": "wx-official-app",
            "openid": "metrics-openid",
            "bind_state": WeChatBindingState.ACTIVE.value,
            "subscribed": True,
            "digest_enabled": True,
        },
    )
    publication_job = client.post(
        f"/admin/digest-issues/{digest_issue['id']}/prepare-publication",
        headers=operator_headers,
    ).json()["publication_jobs"][0]
    client.post(
        f"/admin/digest-publication-jobs/{publication_job['id']}/dispatch",
        headers=operator_headers,
    )
    callback_payload = build_official_account_event_xml(openid="metrics-openid", event="subscribe")
    callback_signature = build_callback_signature("callback-token", "1710000005", "nonce-006")
    client.post(
        "/integrations/wechat/official-account/callback",
        params={
            "signature": callback_signature,
            "timestamp": "1710000005",
            "nonce": "nonce-006",
        },
        content=callback_payload,
        headers={"Content-Type": "application/xml"},
    )

    metrics = client.get("/ops/metrics", headers=operator_headers)

    assert metrics.status_code == 200
    assert "official_account_callback_events_received_total" in metrics.text
    assert "official_account_callback_events_processed_total" in metrics.text
    assert "official_account_binding_updates_total" in metrics.text
    assert "digest_publication_attempts_created_total" in metrics.text
    assert "digest_publication_attempts_failed_total" in metrics.text
    assert "official_account_access_token_refresh_total" in metrics.text
    assert "official_account_access_token_refresh_failed_total" in metrics.text
    assert "official_account_real_dispatch_success_total" in metrics.text
    assert "official_account_real_dispatch_failure_total" in metrics.text
