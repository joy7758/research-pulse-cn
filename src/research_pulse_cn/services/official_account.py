"""Official-account provider boundary and dry-run publisher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from research_pulse_cn.core.config import Settings
from research_pulse_cn.core.errors import ConflictError
from research_pulse_cn.db.models import (
    DigestPublicationJob,
    PulseDigestIssue,
    WeChatIdentityBinding,
)
from research_pulse_cn.domain.enums import (
    DigestPublicationAttemptStatus,
    OfficialAccountProviderMode,
)


@dataclass(slots=True)
class OfficialAccountPublishResult:
    """Outcome from a provider-boundary dispatch call."""

    provider_name: str
    provider_mode: OfficialAccountProviderMode
    attempt_status: DigestPublicationAttemptStatus
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    external_message_id: str | None = None


class OfficialAccountPublisher(Protocol):
    """Provider-ready dispatch boundary for official-account publication."""

    provider_name: str
    provider_mode: OfficialAccountProviderMode

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        """Dispatch or preview a publication job."""


def build_official_account_payload(
    *,
    publication_job: DigestPublicationJob,
    issue: PulseDigestIssue,
    binding: WeChatIdentityBinding,
    settings: Settings,
) -> dict[str, Any]:
    """Build a provider-ready, transport-neutral digest payload."""
    deep_link_path = issue.deep_link_path
    article_url = None
    if deep_link_path and settings.official_account_default_article_base_url:
        article_url = (
            settings.official_account_default_article_base_url.rstrip("/") + deep_link_path
        )

    highlights = []
    for item in issue.items[:3]:
        highlights.append(
            {
                "sort_order": item.sort_order,
                "pulse_card_id": str(item.pulse_card_id),
                "card_type": item.card_type.value,
                "source_paper_id": (
                    None if item.source_paper_id is None else str(item.source_paper_id)
                ),
                "title": item.title,
                "summary": item.summary,
                "why_now": item.why_now,
            }
        )

    return {
        "publication_job_id": str(publication_job.id),
        "digest_issue_id": str(issue.id),
        "title": issue.title,
        "summary": issue.summary,
        "issue_date": issue.issue_date.isoformat(),
        "highlight_count": issue.highlight_count,
        "selected_card_count": issue.selected_card_count,
        "highlights": highlights,
        "landing": {
            "deep_link_path": deep_link_path,
            "mini_program_app_id": settings.official_account_default_mini_program_app_id,
            "mini_program_path": deep_link_path,
            "article_url": article_url,
        },
        "binding": {
            "binding_id": str(binding.id),
            "channel_type": binding.channel_type.value,
            "app_id": binding.app_id,
            "openid": binding.openid,
            "unionid": binding.unionid,
            "display_label": binding.display_label,
        },
        "provider_contract": {
            "publish_target": publication_job.publish_target.value,
            "publish_mode": publication_job.publish_mode.value,
            "provider_mode": settings.official_account_provider_mode.value,
            "dispatch_timeout_seconds": settings.official_account_dispatch_timeout_seconds,
            "external_send_enabled": False,
        },
    }


class DryRunOfficialAccountPublisher:
    """Preview publication jobs without external network calls."""

    provider_name = "wechat_official_account_dry_run"
    provider_mode = OfficialAccountProviderMode.DRY_RUN

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        request_payload = build_official_account_payload(
            publication_job=publication_job,
            issue=issue,
            binding=binding,
            settings=self.settings,
        )
        response_payload = {
            "status": "previewed",
            "provider_name": self.provider_name,
            "provider_mode": self.provider_mode.value,
            "external_send_enabled": False,
            "preview_landing_path": issue.deep_link_path,
        }
        return OfficialAccountPublishResult(
            provider_name=self.provider_name,
            provider_mode=self.provider_mode,
            attempt_status=DigestPublicationAttemptStatus.PREVIEWED,
            request_payload=request_payload,
            response_payload=response_payload,
            external_message_id=None,
        )


class DisabledOfficialAccountPublisher:
    """Block dispatch while keeping the provider boundary explicit."""

    provider_name = "wechat_official_account_disabled"
    provider_mode = OfficialAccountProviderMode.DISABLED

    def dispatch(
        self,
        *,
        publication_job: DigestPublicationJob,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
    ) -> OfficialAccountPublishResult:
        raise ConflictError("official-account provider mode is disabled")


def get_official_account_publisher(settings: Settings) -> OfficialAccountPublisher:
    """Return the configured official-account publisher implementation."""
    if settings.official_account_provider_mode == OfficialAccountProviderMode.DRY_RUN:
        return DryRunOfficialAccountPublisher(settings)
    return DisabledOfficialAccountPublisher()
