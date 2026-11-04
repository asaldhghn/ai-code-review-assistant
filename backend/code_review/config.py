"""Application settings, read from environment variables (and an optional .env file)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import ConfigError

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
DEFAULT_CORS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} must be an integer >= {minimum}.") from None
    if value < minimum:
        raise ConfigError(f"{name} must be an integer >= {minimum}.")
    return value


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # --- AI provider (any OpenAI-compatible API; OpenRouter by default) ---
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    security_model: str = DEFAULT_MODEL
    maintainability_model: str = DEFAULT_MODEL
    # --- hosting policy ---
    enable_live_review: bool = True  # False => demo-only deployment, no AI calls at all
    cors_origins: tuple[str, ...] = DEFAULT_CORS
    live_rate_limit_per_minute: int = 6  # per client IP, live reviews only
    # --- input limits ---
    max_code_chars: int = 60_000
    request_timeout_seconds: int = 120
    # --- agent limits (same meaning as in the original assignment) ---
    max_tool_rounds: int = 6
    max_calls_per_round: int = 8
    max_tokens: int = 4000
    tool_max_chars: int = 20_000
    sdk_max_retries: int = 2


def load_settings() -> Settings:
    """Build Settings from the environment. Raises ConfigError for unusable values."""
    load_dotenv()
    key = (os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip() or None
    shared_model = (os.getenv("REVIEW_MODEL") or DEFAULT_MODEL).strip()
    origins = os.getenv("CORS_ORIGINS")
    cors = DEFAULT_CORS if origins is None else tuple(o.strip() for o in origins.split(",") if o.strip())
    return Settings(
        api_key=key,
        base_url=(os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).strip(),
        security_model=(os.getenv("SECURITY_MODEL") or shared_model).strip(),
        maintainability_model=(os.getenv("MAINTAINABILITY_MODEL") or shared_model).strip(),
        enable_live_review=_bool("ENABLE_LIVE_REVIEW", True),
        cors_origins=cors,
        live_rate_limit_per_minute=_int("LIVE_RATE_LIMIT_PER_MINUTE", 6, 1),
        max_code_chars=_int("MAX_CODE_CHARS", 60_000, 100),
        request_timeout_seconds=_int("REQUEST_TIMEOUT_SECONDS", 120, 5),
        max_tool_rounds=_int("REVIEW_MAX_TOOL_ROUNDS", 6, 1),
        max_calls_per_round=_int("REVIEW_MAX_CALLS_PER_ROUND", 8, 1),
        max_tokens=_int("REVIEW_MAX_TOKENS", 4000, 100),
        tool_max_chars=_int("REVIEW_TOOL_MAX_CHARS", 20_000, 200),
        sdk_max_retries=_int("REVIEW_SDK_MAX_RETRIES", 2, 0),
    )
