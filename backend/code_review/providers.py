"""AI provider integration. Any OpenAI-compatible API works; OpenRouter is the default.

Keeping client creation in one place makes the provider swappable and lets tests inject a fake.
"""

from openai import AsyncOpenAI

from .config import Settings


def create_client(settings: Settings, api_key: str) -> AsyncOpenAI:
    """Create an async client. The base URL comes from server configuration only, never from a
    request, so a caller cannot point the server at an arbitrary host (SSRF)."""
    return AsyncOpenAI(
        base_url=settings.base_url,
        api_key=api_key,
        max_retries=settings.sdk_max_retries,
        timeout=settings.request_timeout_seconds,
    )
