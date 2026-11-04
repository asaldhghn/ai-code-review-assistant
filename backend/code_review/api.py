"""FastAPI application: routes, error handling, security headers and (optionally) the built UI."""

import logging
import os
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import Settings, load_settings
from .errors import RateLimitedError, ReviewError
from .providers import create_client
from .ratelimit import RateLimiter
from .reports import default_report_name, render_html, render_json
from .samples import get_sample, list_samples
from .schemas import (
    LANGUAGE_EXTENSIONS,
    REVIEWER_NAMES,
    ConfigResponse,
    ErrorResponse,
    ReviewRequest,
    ReviewResponse,
    Sample,
    SampleSummary,
)
from .service import ClientFactory, run_review

log = logging.getLogger("code_review.api")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
}
ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


def _error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status, headers=headers)


def find_frontend_dist() -> Path | None:
    """The built UI, if present: $FRONTEND_DIST, or ../frontend/dist next to the backend folder."""
    candidates = [os.getenv("FRONTEND_DIST"), Path(__file__).resolve().parents[2] / "frontend" / "dist"]
    for candidate in candidates:
        if candidate and (Path(candidate) / "index.html").is_file():
            return Path(candidate)
    return None


def create_app(
    settings: Settings | None = None,
    *,
    client_factory: ClientFactory = create_client,
    frontend_dist: Path | None = None,
    clock: Callable[[], float] | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="AI Code Review Assistant",
        version=__version__,
        description="Security and maintainability code review. Demo mode needs no credentials.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    limiter = RateLimiter(settings.live_rate_limit_per_minute, **({"clock": clock} if clock else {}))
    max_body = settings.max_code_chars * 4 + 20_000  # JSON escaping can inflate the code

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Api-Key"],
    )

    @app.middleware("http")
    async def protect(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > max_body:
            return _error(413, "payload_too_large", "The request body is too large.")
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    # ---- error handling: one consistent JSON shape, never echoing input or secrets ----

    @app.exception_handler(ReviewError)
    async def review_error_handler(_: Request, err: ReviewError):
        return _error(err.http_status, err.code, err.message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, err: RequestValidationError):
        first = err.errors()[0] if err.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body") or "request"
        return _error(422, "invalid_input", f"Invalid request: {where}: {first.get('msg', 'invalid value')}.")

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, err: StarletteHTTPException):
        return _error(err.status_code, "http_error", str(err.detail))

    @app.exception_handler(Exception)
    async def unexpected_handler(_: Request, err: Exception):
        log.exception("Unhandled error")  # the traceback stays in server logs only
        return _error(500, "internal_error", "Something went wrong on the server. Please try again.")

    # ---- routes ----

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/config", response_model=ConfigResponse)
    async def config():
        return ConfigResponse(
            version=__version__,
            live_review_enabled=settings.enable_live_review,
            server_key_configured=bool(settings.api_key),
            max_code_chars=settings.max_code_chars,
            languages=list(LANGUAGE_EXTENSIONS),
            reviewers=[{"id": rid, "name": name} for rid, name in REVIEWER_NAMES.items()],
        )

    @app.get("/api/samples", response_model=list[SampleSummary])
    async def samples():
        return list_samples()

    @app.get("/api/samples/{sample_id}", response_model=Sample, responses=ERROR_RESPONSES)
    async def sample(sample_id: str):
        return get_sample(sample_id)

    @app.post("/api/review", response_model=ReviewResponse, responses=ERROR_RESPONSES)
    async def review(request: Request, body: ReviewRequest, x_api_key: str | None = Header(default=None)):
        if body.mode == "live":
            client_ip = request.client.host if request.client else "unknown"
            if not limiter.allow(client_ip):
                raise RateLimitedError("Too many live reviews from this address. Wait a minute and try again.")
        return await run_review(body, settings, api_key=x_api_key, client_factory=client_factory)

    @app.post("/api/reports/{report_format}", responses=ERROR_RESPONSES)
    async def report(report_format: str, review: ReviewResponse):
        if report_format == "json":
            content, media, extension = render_json(review), "application/json", "json"
        elif report_format == "html":
            content, media, extension = render_html(review), "text/html; charset=utf-8", "html"
        else:
            return _error(404, "unknown_format", "Supported report formats: html, json.")
        filename = default_report_name(review, extension)
        return Response(
            content, media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )  # fmt: skip

    # ---- the built single-page app (optional) ----

    dist = frontend_dist if frontend_dist is not None else find_frontend_dist()
    if dist is not None:
        root = dist.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            if path.startswith("api/"):
                return _error(404, "not_found", "No such API route.")
            candidate = (root / path).resolve()
            # Serve real files inside dist only (blocks ../ traversal); everything else is the SPA shell.
            if path and candidate.is_file() and root in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(root / "index.html")

    return app


def app_factory() -> FastAPI:
    """Entry point for `uvicorn code_review.api:app_factory --factory`."""
    return create_app()
