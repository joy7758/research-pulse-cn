"""Minimal in-process metrics registry."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock

COUNTER_NAMES = (
    "scheduler_ticks_total",
    "scheduler_jobs_created_total",
    "pulse_jobs_completed_total",
    "pulse_jobs_failed_total",
    "pulse_cards_selected_total",
    "delivery_jobs_sent_total",
    "delivery_jobs_failed_total",
    "delivery_jobs_dead_letter_total",
    "sync_events_emitted_total",
    "sync_feed_requests_total",
    "sync_mutations_received_total",
    "sync_mutations_applied_total",
    "sync_mutations_failed_total",
    "digest_issues_built_total",
    "digest_publication_jobs_prepared_total",
    "digest_publication_jobs_failed_total",
    "digest_publication_attempts_created_total",
    "digest_publication_attempts_failed_total",
    "mini_read_grants_issued_total",
    "mini_read_grants_revoked_total",
    "mini_read_requests_total",
    "official_account_callback_events_received_total",
    "official_account_callback_events_processed_total",
    "official_account_binding_updates_total",
    "official_account_access_token_refresh_total",
    "official_account_access_token_refresh_failed_total",
    "official_account_real_dispatch_success_total",
    "official_account_real_dispatch_failure_total",
    "work_activity_events_recorded_total",
    "research_watch_profiles_total",
    "pulse_input_previews_total",
    "pulse_yesterday_summary_candidates_total",
    "pulse_yesterday_summary_cards_selected_total",
    "pulse_today_suggestion_candidates_total",
    "pulse_today_suggestion_cards_selected_total",
    "pulse_related_paper_candidates_total",
    "pulse_related_paper_cards_selected_total",
    "external_retrieval_input_previews_total",
    "external_retrieval_plans_built_total",
    "external_retrieval_plans_persisted_total",
    "external_retrieval_runs_started_total",
    "external_retrieval_runs_completed_total",
    "external_retrieval_runs_failed_total",
    "external_retrieval_results_normalized_total",
    "daily_digest_issues_orchestrated_total",
    "daily_digest_publication_prepared_total",
    "daily_digest_preview_requests_total",
    "digest_dispatch_runs_started_total",
    "digest_dispatch_runs_completed_total",
    "digest_dispatch_runs_failed_total",
    "digest_dispatch_jobs_sent_total",
    "digest_delivery_decisions_evaluated_total",
    "digest_delivery_decisions_skipped_total",
    "digest_dispatch_policy_skips_total",
    "subscription_self_service_grants_issued_total",
    "subscription_self_service_bootstrap_requests_total",
    "subscription_self_service_editor_bootstrap_requests_total",
    "subscription_self_service_editor_contract_requests_total",
    "subscription_self_service_settings_preview_requests_total",
    "subscription_self_service_settings_saved_total",
    "subscription_self_service_settings_updated_total",
    "subscription_self_service_delivery_previews_total",
    "official_account_binding_handshake_sessions_created_total",
    "official_account_binding_handshake_sessions_claimed_total",
    "official_account_binding_claim_conflicts_total",
    "official_account_binding_candidates_listed_total",
    "official_account_oauth_authorize_urls_issued_total",
    "official_account_oauth_callbacks_received_total",
    "official_account_oauth_exchange_success_total",
    "official_account_oauth_exchange_failed_total",
    "official_account_oauth_bindings_completed_total",
    "subscription_editor_handoff_grants_issued_total",
    "subscription_editor_handoff_bootstrap_requests_total",
    "subscription_editor_handoff_settings_saved_total",
    "subscription_editor_handoff_grants_revoked_total",
    "group_workspaces_created_total",
    "group_workspace_invite_grants_issued_total",
    "group_workspace_invite_bootstrap_requests_total",
    "group_workspace_invite_claim_previews_total",
    "group_workspace_invite_claims_total",
    "result_share_grants_issued_total",
    "result_share_content_requests_total",
    "group_workspace_result_collect_previews_total",
    "group_workspace_result_collect_actions_total",
    "group_workspace_result_collect_records_created_total",
    "result_share_aliases_issued_total",
    "result_share_alias_resolutions_total",
    "result_share_alias_redirects_total",
)


class MetricsRegistry:
    """Store low-cardinality counters for local observability."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        for name in COUNTER_NAMES:
            self._counters[name] = 0

    def increment(self, name: str, amount: int = 1) -> None:
        """Increase a counter by a positive integer amount."""
        if amount < 0:
            raise ValueError("metrics counters do not support negative increments")
        with self._lock:
            self._counters[name] += amount

    def snapshot(self) -> dict[str, int]:
        """Return a point-in-time copy of counters."""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """Reset counters for tests or local process restarts."""
        with self._lock:
            self._counters.clear()
            for name in COUNTER_NAMES:
                self._counters[name] = 0

    def render_prometheus(self) -> str:
        """Render the registry in Prometheus text exposition format."""
        snapshot = self.snapshot()
        lines: list[str] = []
        for name in sorted(snapshot):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {snapshot[name]}")
        return "\n".join(lines) + "\n"


_METRICS = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    """Return the process metrics singleton."""
    return _METRICS
