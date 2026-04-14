"""Domain service contracts kept separate from infrastructure adapters."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class FactCollector(Protocol):
    """Collect normalized facts for pulse generation."""

    def collect(self, subject_id: str) -> Sequence[Mapping[str, Any]]:
        """Return normalized facts for a given subject."""


class RuleEngine(Protocol):
    """Choose which facts should become pulse candidates."""

    def select(self, facts: Sequence[Mapping[str, Any]]) -> Sequence[Mapping[str, Any]]:
        """Filter or score candidate facts."""


class ModelProvider(Protocol):
    """Generate human-facing card content from structured inputs."""

    def generate(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Produce a card payload."""


class CardValidator(Protocol):
    """Validate generated pulse card payloads before delivery."""

    def validate(self, payload: Mapping[str, Any]) -> bool:
        """Return whether a generated payload is acceptable."""


class ChannelAdapter(Protocol):
    """Send a prepared delivery payload to an outbound channel."""

    def send(self, payload: Mapping[str, Any]) -> None:
        """Dispatch an outbound payload."""
