"""Pydantic models.

Three groups live here:
  * `Finding` / `ReviewResult` - the JSON the AI reviewers must return (sent to the model as a
    strict JSON schema, and used to validate what comes back).
  * `ReadFileArgs` / `RipgrepArgs` plus the OpenAI tool definitions - the CLI-only code tools.
  * `ReviewRequest` / `ReviewResponse` and friends - the public HTTP API contract.
"""

from datetime import datetime
from typing import Literal

import openai
from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["info", "warn", "critical"]
ReviewerId = Literal["security", "maintainability"]
ReviewMode = Literal["demo", "live"]

SEVERITY_ORDER: tuple[Severity, ...] = ("critical", "warn", "info")
REVIEWER_IDS: tuple[ReviewerId, ...] = ("security", "maintainability")
REVIEWER_NAMES = {"security": "Security Auditor", "maintainability": "Maintainability Critic"}

SEVERITY_ALIASES = {
    "warning": "warn",
    "medium": "warn",
    "moderate": "warn",
    "error": "critical",
    "high": "critical",
    "severe": "critical",
    "low": "info",
    "minor": "info",
    "note": "info",
    "suggestion": "info",
}

# Languages the UI offers. The value is also used to name the snippet (snippet.py, ...).
LANGUAGE_EXTENSIONS = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "java": "java",
    "go": "go",
    "csharp": "cs",
    "cpp": "cpp",
    "c": "c",
    "ruby": "rb",
    "php": "php",
    "rust": "rs",
    "sql": "sql",
    "shell": "sh",
    "other": "txt",
}
Language = Literal[
    "python", "javascript", "typescript", "java", "go", "csharp", "cpp", "c",
    "ruby", "php", "rust", "sql", "shell", "other",
]  # fmt: skip


# ---------------------------------------------------------------------------
# What the AI reviewers return
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    """One issue found by a reviewer."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="File the issue is in, exactly as listed in the review input.")
    line: int | None = Field(
        description="1-based line number in the current version of the file, or null if the issue is not tied to one line."
    )
    severity: Severity = Field(description="info = suggestion, warn = should be fixed, critical = must be fixed.")
    category: str = Field(description="Short lowercase category, e.g. security, naming, dead-code.")
    title: str = Field(description="Short headline (under 80 characters) naming the problem.")
    description: str = Field(
        description="What is wrong, naming the specific variable, function or expression involved."
    )
    why_it_matters: str = Field(description="The concrete risk or cost of leaving it as it is.")
    suggestion: str = Field(description="How to fix it, ideally with a short corrected code example.")

    @field_validator("path", mode="before")
    @classmethod
    def _normalize_path(cls, value):
        if isinstance(value, str):
            value = value.strip().replace("\\", "/")
            while value.startswith("./"):
                value = value[2:]
        return value

    @field_validator("line", mode="before")
    @classmethod
    def _normalize_line(cls, value):
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, int) and value < 1:
            return None
        return value

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            value = SEVERITY_ALIASES.get(value, value)
        return value

    @field_validator("path", "category", "title", "description", "why_it_matters", "suggestion", mode="before")
    @classmethod
    def _strip_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("path", "category", "title", "description", "why_it_matters", "suggestion")
    @classmethod
    def _not_empty(cls, value):
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("category")
    @classmethod
    def _lowercase_category(cls, value):
        return value.lower()


class CheckedFinding(Finding):
    """A finding after our own checks. These extra fields are never sent to the model."""

    # "added" / "context": line verified in the diff; "valid": line exists in the file;
    # "unverified": the model's line was not valid (line was cleared); "none": no line given.
    line_status: str = "none"
    claimed_line: int | None = None  # the model's line when it was unverified


class ReviewResult(BaseModel):
    """The JSON object each reviewer must return."""

    model_config = ConfigDict(extra="forbid")

    findings: list[Finding] = Field(description="All issues found; an empty list if there are none.")


# ---------------------------------------------------------------------------
# CLI-only tools the reviewers may call
# ---------------------------------------------------------------------------


class ReadFileArgs(BaseModel):
    """Arguments for the read_file tool."""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(description="Path of the file, relative to the repository root, e.g. 'src/app.py'.")
    start_line: int | None = Field(description="1-based first line to read, or null to start at line 1.")
    end_line: int | None = Field(description="1-based last line to read (inclusive), or null to read to the end.")


class RipgrepArgs(BaseModel):
    """Arguments for the ripgrep tool."""

    model_config = ConfigDict(extra="forbid")

    search_pattern: str = Field(
        description="Regular expression to search for, e.g. 'def calculate_tax' or 'api_key|password'."
    )


READ_FILE_TOOL = openai.pydantic_function_tool(
    ReadFileArgs,
    name="read_file",
    description=(
        "Read a text file in the repository and return numbered lines. Use it to see code the "
        "diff does not show: imports, class or function definitions, surrounding lines, config "
        "files. Request a focused line range. Output is capped at 400 lines per call."
    ),
)

RIPGREP_TOOL = openai.pydantic_function_tool(
    RipgrepArgs,
    name="ripgrep",
    description=(
        "Search the whole repository recursively with ripgrep (regular expression). Returns "
        "path:line:text for each match. Use it to find where a function is defined, who calls "
        "it, or whether a risky pattern appears elsewhere. Secret files and .gitignore'd files "
        "are not searched."
    ),
)

TOOLS = [READ_FILE_TOOL, RIPGREP_TOOL]
TOOL_ARG_MODELS = {"read_file": ReadFileArgs, "ripgrep": RipgrepArgs}


# ---------------------------------------------------------------------------
# Public HTTP API
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    """Body of POST /api/review."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Source code to review. Never executed.")
    language: Language = "python"
    filename: str | None = Field(default=None, max_length=120, description="Optional display name.")
    reviewers: list[ReviewerId] = Field(default_factory=lambda: list(REVIEWER_IDS), min_length=1)
    mode: ReviewMode = "demo"

    @field_validator("filename")
    @classmethod
    def _clean_filename(cls, value):
        if value is None:
            return None
        # The name is only a label. Drop directories and control characters.
        name = value.strip().replace("\\", "/").split("/")[-1]
        name = "".join(ch for ch in name if ch.isprintable())
        return name or None

    @field_validator("reviewers")
    @classmethod
    def _unique_reviewers(cls, value):
        return list(dict.fromkeys(value))


class ApiFinding(BaseModel):
    """A finding as shown to API clients."""

    id: str
    reviewer: ReviewerId
    title: str
    severity: Severity
    category: str
    path: str
    line: int | None
    description: str
    why_it_matters: str
    suggestion: str


class ReviewerStatus(BaseModel):
    id: ReviewerId
    name: str
    status: Literal["ok", "failed"]
    engine: str = Field(description="Model name for live reviews, or the demo engine label.")
    finding_count: int = 0
    error_code: str | None = None
    error_message: str | None = None


class SeverityCounts(BaseModel):
    critical: int = 0
    warn: int = 0
    info: int = 0


class ReviewerCounts(BaseModel):
    security: int = 0
    maintainability: int = 0


class ReviewSummary(BaseModel):
    total: int
    by_severity: SeverityCounts
    by_reviewer: ReviewerCounts


class ReviewResponse(BaseModel):
    """Result of one review. `is_demo` is true for rule-based demo output (no AI involved)."""

    review_id: str
    mode: ReviewMode
    is_demo: bool
    status: Literal["complete", "partial"]
    created_at: datetime
    language: Language
    filename: str
    line_count: int
    summary: ReviewSummary
    reviewers: list[ReviewerStatus]
    findings: list[ApiFinding]
    notices: list[str] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class SampleSummary(BaseModel):
    id: str
    title: str
    language: Language
    filename: str
    description: str


class Sample(SampleSummary):
    code: str


class ConfigResponse(BaseModel):
    version: str
    live_review_enabled: bool
    server_key_configured: bool
    max_code_chars: int
    languages: list[str]
    reviewers: list[dict[str, str]]
