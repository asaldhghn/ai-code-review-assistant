"""Typed errors shared by the API, the CLI and the reviewer agents.

Every error carries a stable machine-readable `code` and a message that is safe to
show to a user (it never contains credentials).
"""


class ReviewError(Exception):
    code = "review_error"
    http_status = 500

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class InvalidInputError(ReviewError):
    code = "invalid_input"
    http_status = 422


class PayloadTooLargeError(InvalidInputError):
    code = "payload_too_large"
    http_status = 413


class LiveReviewDisabledError(ReviewError):
    code = "live_review_disabled"
    http_status = 403


class MissingCredentialsError(ReviewError):
    code = "missing_credentials"
    http_status = 401


class InvalidCredentialsError(ReviewError):
    code = "invalid_credentials"
    http_status = 401


class RateLimitedError(ReviewError):
    code = "rate_limited"
    http_status = 429


class ProviderUnavailableError(ReviewError):
    """Network failure, timeout, or a 5xx from the AI provider."""

    code = "provider_unavailable"
    http_status = 502


class ProviderError(ReviewError):
    code = "provider_error"
    http_status = 502


class InvalidModelResponseError(ReviewError):
    code = "invalid_response"
    http_status = 502


class ConfigError(Exception):
    """An environment variable has an unusable value (startup / CLI problem)."""
