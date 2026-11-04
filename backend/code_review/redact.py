"""Keep secrets out of logs and error messages."""

import logging
import re

# Patterns for credentials that commonly leak through exception text.
_SK_KEY = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}")
_API_KEY_ASSIGNMENT = re.compile(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9._\-]{8,}")

_registered: list[str] = []


def register_secret(value: str | None) -> None:
    """Remember a secret (like the CLI's API key) so it is masked in all log output."""
    if value and len(value) >= 8 and value not in _registered:
        _registered.append(value)


def scrub(text: object, secrets: tuple[str, ...] | list[str] = ()) -> str:
    """Return `text` with registered secrets, the given secrets, and key-like strings masked."""
    result = str(text)
    for secret in (*_registered, *secrets):
        if secret and len(secret) >= 8:
            result = result.replace(secret, "[REDACTED]")
    result = _SK_KEY.sub("[REDACTED]", result)
    result = _BEARER.sub("Bearer [REDACTED]", result)
    return _API_KEY_ASSIGNMENT.sub(r"\1[REDACTED]", result)


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs the formatted message of every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = scrub(record.getMessage())
        record.args = None
        return True


def configure_logging(debug: bool) -> None:
    """Send redacted log lines to stderr (used by the CLI)."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger("code_review")
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.WARNING)
    root.propagate = False
