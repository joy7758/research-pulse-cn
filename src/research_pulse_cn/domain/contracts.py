"""Domain service contracts kept separate from infrastructure adapters."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from research_pulse_cn.domain.pulse import PulseCandidate, PulseFact


class FactCollector(Protocol):
    """Collect normalized facts for pulse generation."""

    def collect(self, subject_id: str) -> Sequence[PulseFact]:
        """Return normalized facts for a given subject."""


class RuleEngine(Protocol):
    """Choose which facts should become pulse candidates."""

    def generate_candidates(self, facts: Sequence[PulseFact]) -> Sequence[PulseCandidate]:
        """Convert normalized facts into pulse candidates."""


class ModelProvider(Protocol):
    """Generate human-facing card content from structured inputs."""

    def generate(self, payload: PulseCandidate) -> Mapping[str, Any]:
        """Produce a card payload."""


class CardValidator(Protocol):
    """Validate generated pulse card payloads before delivery."""

    def validate(self, payload: Mapping[str, Any]) -> bool:
        """Return whether a generated payload is acceptable."""


class ChannelAdapter(Protocol):
    """Send a prepared delivery payload to an outbound channel."""

    def send(self, payload: Mapping[str, Any]) -> None:
        """Dispatch an outbound payload."""
