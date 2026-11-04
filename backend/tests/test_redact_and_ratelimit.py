import logging

from code_review.ratelimit import RateLimiter
from code_review.redact import RedactingFilter, register_secret, scrub


def test_scrub_masks_explicit_secrets_and_key_shaped_strings():
    assert "hunter2hunter2" not in scrub("password is hunter2hunter2", ("hunter2hunter2",))
    assert "sk-or-v1-abcdef123456" not in scrub("key sk-or-v1-abcdef123456 failed")
    assert "abcdefgh12345" not in scrub("Authorization: Bearer abcdefgh12345")
    assert "supersecretvalue" not in scrub('{"api_key": "supersecretvalue"}')


def test_scrub_leaves_ordinary_text_alone():
    assert scrub("nothing to hide here") == "nothing to hide here"


def test_registered_secrets_are_masked_in_log_records():
    register_secret("registered-secret-value")
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "token=%s", ("registered-secret-value",), None)
    RedactingFilter().filter(record)
    assert "registered-secret-value" not in record.getMessage()


def test_rate_limiter_allows_up_to_limit_then_blocks_and_recovers():
    now = [0.0]
    limiter = RateLimiter(2, window_seconds=60, clock=lambda: now[0])
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")  # separate client
    now[0] = 61
    assert limiter.allow("a")
