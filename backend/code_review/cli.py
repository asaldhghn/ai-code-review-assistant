"""Command-line interface.

    code-review                     review the staged git changes (git diff --staged)
    code-review --file app.py       review one file
    code-review --demo --file x.py  rule-based demo review, no API key needed

Run as `python -m code_review` if the `code-review` script is not on your PATH.
"""

import argparse
import asyncio
import contextlib
import logging
import os
import subprocess
import sys
from datetime import datetime

from . import __version__, tools
from .agents import ReviewerOutcome, ReviewInput, file_display_path, run_reviewers
from .config import Settings, load_settings
from .demo import DEMO_ENGINE, run_demo_reviewer
from .diffs import parse_diff
from .errors import ConfigError, ReviewError
from .providers import create_client
from .redact import configure_logging, register_secret, scrub
from .reports import render_html, render_json
from .schemas import LANGUAGE_EXTENSIONS, REVIEWER_IDS, CheckedFinding, ReviewerId
from .service import DEMO_NOTICE, assemble_response

log = logging.getLogger("code_review.cli")

EXTENSION_LANGUAGES = {ext: lang for lang, ext in LANGUAGE_EXTENSIONS.items() if lang != "other"}
EXTENSION_LANGUAGES.update({"jsx": "javascript", "tsx": "typescript", "h": "c", "hpp": "cpp", "cc": "cpp"})


def fail(message: str) -> None:
    """Print an error to stderr and exit with a nonzero code."""
    print(f"Error: {scrub(message)}", file=sys.stderr)
    sys.exit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="code-review",
        description="AI code review of staged git changes (default) or a single file.",
        epilog="Live AI reviews need LLM_API_KEY (or OPENROUTER_API_KEY) in the environment or a .env file.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--file", metavar="PATH", help="review this file instead of the staged git changes")
    parser.add_argument(
        "--reviewers", default=",".join(REVIEWER_IDS), metavar="LIST",
        help="comma-separated reviewers to run: security, maintainability (default: both)",
    )  # fmt: skip
    parser.add_argument(
        "--demo", action="store_true",
        help="use the deterministic rule-based demo engine instead of an AI model (no API key, no cost)",
    )  # fmt: skip
    parser.add_argument("--format", choices=("html", "json"), default="html", help="report format (default: html)")
    parser.add_argument(
        "--output", metavar="FILENAME",
        help="where to save the report (default: review-YYYYMMDD-HHMMSS.html or .json)",
    )  # fmt: skip
    parser.add_argument(
        "--no-tools", action="store_true",
        help="do not let the AI call read_file/ripgrep (it then reviews only the supplied code)",
    )  # fmt: skip
    parser.add_argument("--debug", action="store_true", help="print detailed logs to stderr (secrets are redacted)")
    return parser.parse_args(argv)


def parse_reviewers(raw: str) -> list[ReviewerId]:
    names = [part.strip().lower() for part in raw.split(",") if part.strip()]
    unknown = [n for n in names if n not in REVIEWER_IDS]
    if not names or unknown:
        fail(
            f"unknown reviewer {unknown[0]!r}. Choose from: {', '.join(REVIEWER_IDS)}."
            if unknown
            else "no reviewers selected."
        )
    return list(dict.fromkeys(names))  # type: ignore[arg-type]


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    """Run a git command and return the CompletedProcess, or exit if git cannot run."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )
    except FileNotFoundError:
        fail("git was not found. Install git and make sure it is on your PATH.")
    except (OSError, subprocess.SubprocessError) as err:
        fail(f"could not run git: {err}")
    raise AssertionError("unreachable")


def first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0] if lines else "no error message from git"


def get_staged_diff() -> str:
    """Return the output of `git diff --staged`, or exit with a useful error."""
    check = run_git(["rev-parse", "--is-inside-work-tree"])
    if check.returncode != 0 or check.stdout.strip() != "true":
        fail("not inside a git repository. Run this from a repo, or use --file PATH.")

    # Explicit flags keep the diff format fixed whatever the user's git config says;
    # paths in the output are relative to the repository root, not the current directory.
    result = run_git([
        "-c", "core.quotepath=off", "diff", "--staged", "--no-ext-diff", "--no-color", "-M",
        "--src-prefix=a/", "--dst-prefix=b/",
    ])  # fmt: skip
    if result.returncode != 0:
        fail(f"git diff --staged failed (exit code {result.returncode}): {first_line(result.stderr)}")
    if not result.stdout.strip():
        fail("No staged changes to review. Stage changes with 'git add' and try again.")
    return result.stdout


def read_input_file(path: str, max_chars: int) -> str:
    """Return the text of a local file, or exit with a useful error."""
    if os.path.isdir(path):
        fail(f"'{path}' is a directory, not a file.")
    try:
        with open(path, encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        fail(f"file not found: {path}")
    except PermissionError:
        fail(f"permission denied reading '{path}'.")
    except UnicodeDecodeError:
        fail(f"'{path}' is not a UTF-8 text file and cannot be reviewed.")
    except OSError as err:
        fail(f"could not read '{path}': {err}")
    if not content.strip():
        fail(f"'{path}' is empty; nothing to review.")
    if len(content) > max_chars:
        fail(f"'{path}' has {len(content):,} characters; the limit is {max_chars:,} (set MAX_CODE_CHARS to change it).")
    return content


def default_output_name(fmt: str, now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime(f"review-%Y%m%d-%H%M%S.{fmt}")


def check_output_path(path: str) -> str | None:
    """Return an error message if the report cannot be written to `path`, else None."""
    if not path or not path.strip():
        return "the output filename is empty."
    if os.path.isdir(path):
        return f"'{path}' is a directory; give a file name."
    folder = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(folder):
        return f"the folder for '{path}' does not exist."
    target_ok = os.access(path, os.W_OK) if os.path.exists(path) else os.access(folder, os.W_OK)
    return None if target_ok else f"permission denied writing '{path}'."


def print_outcomes(outcomes: list[ReviewerOutcome]) -> None:
    for outcome in outcomes:
        if outcome.error:
            print(f"{outcome.id} ({outcome.model}): FAILED - {outcome.error.message}")
            continue
        print(f"{outcome.id} ({outcome.model}): {len(outcome.findings)} finding(s)")
        for finding in outcome.findings:
            where = finding.path if finding.line is None else f"{finding.path}:{finding.line}"
            print(f"  [{finding.severity}] {where} ({finding.category}) {finding.title}")


def demo_outcomes(review_input: ReviewInput, reviewers: list[ReviewerId], language: str) -> list[ReviewerOutcome]:
    outcomes = []
    for reviewer in reviewers:
        findings: list[CheckedFinding] = []
        for path in review_input.paths:
            findings += [
                CheckedFinding(**f.model_dump(), line_status="valid" if f.line else "none")
                for f in run_demo_reviewer(reviewer, review_input.content, language, path)
            ]
        outcomes.append(ReviewerOutcome(reviewer, DEMO_ENGINE, findings))
    return outcomes


async def live_outcomes(
    settings: Settings, review_input: ReviewInput, reviewers: list[ReviewerId], tools_enabled: bool
) -> list[ReviewerOutcome]:
    if not settings.api_key:
        fail(
            "no API key found. Set LLM_API_KEY (or OPENROUTER_API_KEY) in your environment or .env file, or use --demo."
        )
    register_secret(settings.api_key)
    client = create_client(settings, settings.api_key)
    try:
        return await run_reviewers(
            client, review_input, settings, reviewers, tools_enabled=tools_enabled, secrets=(settings.api_key,)
        )
    finally:
        await client.close()


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):  # never crash on characters the console cannot show
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(errors="replace")

    args = parse_args(argv)
    configure_logging(args.debug)
    try:
        settings = load_settings()
    except ConfigError as err:
        fail(str(err))
    reviewers = parse_reviewers(args.reviewers)

    output = args.output or default_output_name(args.format)
    problem = check_output_path(output)
    if problem:
        fail(problem)

    # One repository root for everything: the git diff, read_file and ripgrep.
    tools.set_repo_root(tools.find_repo_root())
    log.debug("Repository root: %s", tools.REPO_ROOT)

    if args.file:
        mode, source = "file", args.file
        content = read_input_file(args.file, settings.max_code_chars)
        paths = [file_display_path(args.file)]
        review_input = ReviewInput("file", content, paths)
        extension = os.path.splitext(args.file)[1].lstrip(".").lower()
        language = EXTENSION_LANGUAGES.get(extension, "other")
    else:
        if args.demo:
            fail("--demo reviews whole files; use --file PATH (the demo scanner does not read diffs).")
        mode, source = "git", "git diff --staged"
        content = get_staged_diff()
        diff = parse_diff(content)
        if not diff.paths:
            fail("could not find any file paths in the staged diff.")
        review_input = ReviewInput("git", content, diff.paths, diff)
        language = "other"

    engine = "demo" if args.demo else "AI"
    print(f"Mode: {mode} ({source}), {len(content)} characters read, engine: {engine}")

    if args.demo:
        outcomes = demo_outcomes(review_input, reviewers, language)
        notices = [DEMO_NOTICE]
    else:
        outcomes = asyncio.run(live_outcomes(settings, review_input, reviewers, tools_enabled=not args.no_tools))
        notices = []

    print_outcomes(outcomes)
    if all(o.error for o in outcomes):
        sys.exit(1)

    review = assemble_response(
        outcomes, mode="demo" if args.demo else "live", language=language,
        filename=", ".join(review_input.paths), line_count=len(content.splitlines()), notices=notices,
        engine_labels={o.id: DEMO_ENGINE for o in outcomes} if args.demo else None,
    )  # fmt: skip
    report = render_json(review) if args.format == "json" else render_html(review)
    try:
        with open(output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(report)
    except OSError as err:
        fail(f"could not write the report to '{output}': {err}")
    for outcome in outcomes:
        if outcome.error:
            print(f"Warning: {outcome.id} reviewer failed: {outcome.error.message}", file=sys.stderr)
    print(f"Report saved to: {output}")


if __name__ == "__main__":
    try:
        main()
    except ReviewError as err:
        fail(err.message)
