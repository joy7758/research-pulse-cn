"""Shared application exceptions."""


class ResearchPulseError(Exception):
    """Base application error."""


class NotFoundError(ResearchPulseError):
    """Raised when an entity cannot be found."""


class ConflictError(ResearchPulseError):
    """Raised when a write would violate a uniqueness or state constraint."""


class ValidationFailedError(ResearchPulseError):
    """Raised when deterministic validation rejects a generated payload."""


class DeliveryDispatchError(ResearchPulseError):
    """Raised when a delivery adapter cannot dispatch a payload."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class AuthenticationError(ResearchPulseError):
    """Raised when a caller cannot be authenticated."""


class AuthorizationError(ResearchPulseError):
    """Raised when a caller is authenticated but not allowed to perform an action."""
