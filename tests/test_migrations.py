from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_core_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'alembic.sqlite3'}"
    repo_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(repo_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert {
        "admin_accounts",
        "admin_refresh_tokens",
        "audit_logs",
        "client_devices",
        "client_access_tokens",
        "digest_publication_jobs",
        "digest_publication_attempts",
        "digest_dispatch_runs",
        "mini_read_grants",
        "subscription_self_service_grants",
        "official_account_binding_handshake_sessions",
        "official_account_callback_events",
        "sync_events",
        "sync_cursors",
        "sync_mutations",
        "user_profiles",
        "paper_profiles",
        "progress_events",
        "signal_snapshots",
        "subscription_policies",
        "pulse_jobs",
        "pulse_cards",
        "pulse_digest_issues",
        "pulse_digest_items",
        "delivery_jobs",
        "external_retrieval_plans",
        "external_retrieval_runs",
        "external_retrieved_records",
        "wechat_identity_bindings",
        "worker_heartbeats",
        "delivery_attempts",
    }.issubset(table_names)
    pulse_card_columns = {column["name"] for column in inspector.get_columns("pulse_cards")}
    assert {
        "source_paper_id",
        "score_total",
        "score_breakdown",
        "candidate_metadata",
    }.issubset(pulse_card_columns)
    pulse_job_columns = {column["name"] for column in inspector.get_columns("pulse_jobs")}
    assert {
        "subscription_policy_id",
        "scheduled_reason",
        "schedule_key",
        "started_at",
        "completed_at",
        "failed_at",
        "lease_owner",
        "lease_expires_at",
    }.issubset(pulse_job_columns)
    admin_account_columns = {column["name"] for column in inspector.get_columns("admin_accounts")}
    assert {
        "email",
        "password_hash",
        "role",
        "is_active",
        "must_change_password",
        "last_login_at",
    }.issubset(admin_account_columns)
    refresh_token_columns = {
        column["name"] for column in inspector.get_columns("admin_refresh_tokens")
    }
    assert {
        "admin_account_id",
        "token_hash",
        "issued_at",
        "expires_at",
        "revoked_at",
        "last_used_at",
    }.issubset(refresh_token_columns)
    audit_log_columns = {column["name"] for column in inspector.get_columns("audit_logs")}
    assert {
        "actor_type",
        "actor_id",
        "action",
        "request_id",
        "route",
        "method",
        "status_code",
        "metadata",
        "created_at",
    }.issubset(audit_log_columns)
    client_device_columns = {column["name"] for column in inspector.get_columns("client_devices")}
    assert {
        "user_id",
        "client_type",
        "display_name",
        "is_active",
        "last_seen_at",
    }.issubset(client_device_columns)
    client_access_token_columns = {
        column["name"] for column in inspector.get_columns("client_access_tokens")
    }
    assert {
        "client_device_id",
        "token_hash",
        "issued_at",
        "expires_at",
        "revoked_at",
        "last_used_at",
    }.issubset(client_access_token_columns)
    sync_event_columns = {column["name"] for column in inspector.get_columns("sync_events")}
    assert {
        "sequence",
        "user_id",
        "entity_type",
        "entity_id",
        "event_type",
        "payload",
        "event_source",
        "occurred_at",
    }.issubset(sync_event_columns)
    sync_cursor_columns = {column["name"] for column in inspector.get_columns("sync_cursors")}
    assert {
        "client_device_id",
        "last_event_sequence",
        "last_synced_at",
        "updated_at",
    }.issubset(sync_cursor_columns)
    sync_mutation_columns = {column["name"] for column in inspector.get_columns("sync_mutations")}
    assert {
        "client_device_id",
        "client_mutation_id",
        "mutation_type",
        "resource_type",
        "resource_id",
        "payload",
        "status",
        "error_message",
        "resulting_event_sequence",
        "created_at",
        "applied_at",
    }.issubset(sync_mutation_columns)
    binding_columns = {
        column["name"] for column in inspector.get_columns("wechat_identity_bindings")
    }
    assert {
        "user_id",
        "channel_type",
        "app_id",
        "openid",
        "unionid",
        "bind_state",
        "subscribed",
        "digest_enabled",
        "metadata",
    }.issubset(binding_columns)
    external_retrieval_columns = {
        column["name"] for column in inspector.get_columns("external_retrieval_plans")
    }
    assert {
        "user_id",
        "source_kind",
        "retrieval_scope",
        "watch_profile_id",
        "paper_id",
        "plan_label",
        "query_text",
        "query_payload",
        "effective_inputs",
        "reason_codes",
        "plan_hash",
        "status",
        "created_at",
        "updated_at",
    }.issubset(external_retrieval_columns)
    external_retrieval_run_columns = {
        column["name"] for column in inspector.get_columns("external_retrieval_runs")
    }
    assert {
        "plan_id",
        "user_id",
        "source_kind",
        "retrieval_scope",
        "status",
        "request_url",
        "request_payload",
        "response_summary",
        "raw_result_count",
        "normalized_result_count",
        "started_at",
        "finished_at",
        "last_error",
        "created_at",
        "updated_at",
    }.issubset(external_retrieval_run_columns)
    external_retrieved_record_columns = {
        column["name"] for column in inspector.get_columns("external_retrieved_records")
    }
    assert {
        "run_id",
        "plan_id",
        "user_id",
        "source_kind",
        "retrieval_scope",
        "external_id",
        "external_url",
        "doi",
        "title",
        "abstract_snippet",
        "publication_year",
        "publication_date",
        "source_title",
        "authors",
        "matched_reason_codes",
        "raw_payload",
        "sort_order",
        "created_at",
        "updated_at",
    }.issubset(external_retrieved_record_columns)
    digest_dispatch_run_columns = {
        column["name"] for column in inspector.get_columns("digest_dispatch_runs")
    }
    assert {
        "digest_issue_id",
        "user_id",
        "publish_target",
        "dispatch_mode",
        "provider_mode",
        "status",
        "total_jobs",
        "eligible_jobs",
        "previewed_jobs",
        "sent_jobs",
        "failed_jobs",
        "skipped_jobs",
        "started_at",
        "finished_at",
        "last_error",
        "created_at",
        "updated_at",
    }.issubset(digest_dispatch_run_columns)
    digest_publication_attempt_columns = {
        column["name"] for column in inspector.get_columns("digest_publication_attempts")
    }
    assert {
        "dispatch_run_id",
        "provider_name",
        "provider_mode",
        "status",
        "request_payload",
        "response_payload",
        "error_summary",
        "external_message_id",
        "provider_response_code",
        "provider_response_message",
        "started_at",
        "finished_at",
    }.issubset(digest_publication_attempt_columns)
    digest_issue_columns = {
        column["name"] for column in inspector.get_columns("pulse_digest_issues")
    }
    assert {
        "user_id",
        "issue_date",
        "source_pulse_job_id",
        "status",
        "highlight_count",
        "selected_card_count",
        "deep_link_path",
        "content_payload",
        "build_metadata",
    }.issubset(digest_issue_columns)
    digest_item_columns = {column["name"] for column in inspector.get_columns("pulse_digest_items")}
    assert {
        "digest_issue_id",
        "pulse_card_id",
        "sort_order",
        "card_type",
        "source_paper_id",
        "why_now",
    }.issubset(digest_item_columns)
    publication_job_columns = {
        column["name"] for column in inspector.get_columns("digest_publication_jobs")
    }
    assert {
        "digest_issue_id",
        "binding_id",
        "publish_target",
        "status",
        "publish_mode",
        "provider_name",
        "payload",
        "prepared_at",
    }.issubset(publication_job_columns)
    publication_attempt_columns = {
        column["name"] for column in inspector.get_columns("digest_publication_attempts")
    }
    assert {
        "digest_publication_job_id",
        "attempt_number",
        "provider_name",
        "provider_mode",
        "status",
        "request_payload",
        "response_payload",
        "error_summary",
        "external_message_id",
        "provider_response_code",
        "provider_response_message",
        "started_at",
        "finished_at",
    }.issubset(publication_attempt_columns)
    mini_grant_columns = {column["name"] for column in inspector.get_columns("mini_read_grants")}
    assert {
        "user_id",
        "binding_id",
        "digest_issue_id",
        "grant_type",
        "token_hash",
        "status",
        "scope",
        "expires_at",
        "last_used_at",
        "created_by_admin_id",
    }.issubset(mini_grant_columns)
    self_service_grant_columns = {
        column["name"] for column in inspector.get_columns("subscription_self_service_grants")
    }
    assert {
        "user_id",
        "binding_id",
        "channel",
        "grant_scope",
        "token_hash",
        "status",
        "display_label",
        "issued_by_admin_id",
        "expires_at",
        "last_used_at",
        "created_at",
        "updated_at",
    }.issubset(self_service_grant_columns)
    handshake_session_columns = {
        column["name"]
        for column in inspector.get_columns("official_account_binding_handshake_sessions")
    }
    assert {
        "user_id",
        "channel",
        "app_id",
        "display_label",
        "self_service_grant_id",
        "issued_by_admin_id",
        "state_token_hash",
        "requested_scope",
        "authorized_scope",
        "oauth_openid_hash",
        "status",
        "matched_callback_event_id",
        "claimed_binding_id",
        "expires_at",
        "last_viewed_at",
        "authorization_started_at",
        "matched_at",
        "claimed_at",
        "oauth_completed_at",
        "userinfo_fetched",
        "last_error",
        "created_at",
        "updated_at",
    }.issubset(handshake_session_columns)
    callback_event_columns = {
        column["name"] for column in inspector.get_columns("official_account_callback_events")
    }
    assert {
        "app_id",
        "to_user_name",
        "from_openid",
        "msg_type",
        "event_type",
        "event_key",
        "event_time",
        "dedupe_key",
        "signature_valid",
        "payload_format",
        "raw_payload",
        "parsed_payload",
        "processing_status",
        "processing_note",
        "linked_binding_id",
        "created_at",
        "processed_at",
    }.issubset(callback_event_columns)
