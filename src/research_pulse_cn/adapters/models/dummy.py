"""Deterministic model provider used for early pulse generation."""

from typing import Any

from research_pulse_cn.domain.enums import PulseCardType


class DummyModelProvider:
    """Generate stable pulse card copy from deterministic facts."""

    TITLES = {
        PulseCardType.NEXT_ACTION: "Next action ready",
        PulseCardType.STALLED_PROGRESS: "Progress appears stalled",
        PulseCardType.SIGNAL_CHANGE: "Signal update detected",
        PulseCardType.DEADLINE_RISK: "Deadline risk identified",
        PulseCardType.RELATED_PAPER: "Related paper worth reviewing",
    }

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        card_type = payload["card_type"]
        paper_title = payload["paper_title"]
        title_prefix = self.TITLES.get(card_type, "Pulse update")
        return {
            "card_type": card_type,
            "priority": payload["priority"],
            "title": f"{title_prefix}: {paper_title}",
            "summary": payload["summary"],
            "why_now": payload["why_now"],
            "action_text": payload.get("action_text"),
            "deep_link": payload.get("deep_link"),
            "evidence_refs": list(payload.get("evidence_refs", [])),
            "generated_by": {
                "provider": "dummy-model-provider",
                "mode": "deterministic",
            },
        }
