# 03 · Backend walkthrough

All backend code lives in `backend/code_review/`. Read the files in this order.

## `schemas.py`: the data shapes

Pydantic models describe data and validate it. Three groups:

1. **What the AI must return**: `Finding` and `ReviewResult`. A `Finding` has `path`, `line`, `severity`, `category`, `title`, `description`, `why_it_matters`, `suggestion`. The validators are forgiving where models are sloppy (severity `"high"` becomes `"critical"`, line `"7"` becomes `7`) and strict where it matters (empty text is rejected, unknown fields are rejected).
2. **Tool arguments**: `ReadFileArgs`, `RipgrepArgs` (CLI only).
3. **The public API**: `ReviewRequest`, `ReviewResponse`, `ApiFinding`, `ReviewerStatus`, and so on.

`ReviewRequest` shows a good habit: `ConfigDict(extra="forbid")` rejects typos like `"reviwers"`, and a validator reduces `filename` to a bare label (`../../etc/passwd` becomes `passwd`).

## `config.py`: settings

`load_settings()` reads environment variables (and a `.env` file) into a frozen `Settings` dataclass. Bad values raise `ConfigError` with a clear message. Nothing is hardcoded, and the API key is only ever read from the environment or a request header.

## `service.py`: the orchestrator

- `validate_code()` rejects empty, binary (NUL bytes) and oversized input.
- `run_review()` is the main function for the API. It picks demo or live, enforces `enable_live_review`, finds a key, runs the reviewers under `asyncio.wait_for(...)` (a timeout), and always closes the client in `finally`.
- `assemble_response()` builds the final `ReviewResponse`; the CLI uses it too.

## `agents.py`: the AI reviewers

This is the ported assignment code. The important functions:

| Function | Job |
| --- | --- |
| `load_prompt()` | Reads `prompts/security.md` or `maintainability.md`. With tools off it replaces the marked tools section with "no tools are available". |
| `build_user_prompt()` | Wraps the code in a fence **longer than any backticks inside it**, so code cannot break out of its block. |
| `_chat()` | One model call. Handles the provider rejecting `tool_choice="required"` by retrying with `"auto"`. |
| `_tool_loop()` | Lets the model call tools for up to `max_tool_rounds`, then forces a final answer (CLI only). |
| `parse_result()` | Parses the model's JSON (tolerates a markdown fence) into `ReviewResult`. |
| `clean_findings()` | Drops findings for files that are not in the review, verifies line numbers, removes duplicates. |
| `translate_api_error()` | Maps OpenAI SDK exceptions to our typed errors without leaking secrets. |
| `run_reviewer()` | Runs one reviewer and **never raises**; failure is stored in the outcome so the other reviewer can still succeed. |

## `diffs.py`: line verification for git diffs

`parse_diff()` walks a unified diff and records which new-file line numbers are added or context lines. If a model claims "line 99" but the diff never showed line 99, `check_line()` says `unverified` and the line number is removed rather than shown as fact. For single files the line just has to exist.

## `tools.py`: the safe file tools (CLI only)

`read_file()` and `ripgrep()` return errors as text (`"ERROR: ..."`) instead of raising, so the model can read the message and adapt. Safety lives in `_resolve_inside_repo()`: it resolves symlinks with `os.path.realpath`, requires the result to be inside the repository root, and `_is_sensitive()` blocks `.env`, `.git`, keys and certificates. `tests/test_tools_security.py` proves those rules.

## `demo.py`: the rule-based engine

A list of `Rule` objects (regex plus explanation text) and some Python `ast` checks (unused imports, long functions, duplicate function bodies, undefined names, swallowed exceptions). Details worth knowing:

- `code_only=True` rules ignore text inside string literals, so `"call eval(x)"` in a message is not flagged.
- Each rule is capped at 5 hits so one bad pattern cannot flood the result.
- Results are sorted by severity then line, so output is deterministic.

## `reports.py`: HTML and JSON

`render_html()` builds the page from validated data and passes **every** value through `html.escape`. That is why a finding titled `<script>alert(1)</script>` is harmless; `tests/test_api.py::test_html_report_escapes_untrusted_content` checks it.

## `api.py`: the web layer

`create_app()` is a factory: tests build an app with fake settings and a fake AI client, production builds it from the environment. It sets up CORS, a middleware that rejects huge bodies and adds security headers, the exception handlers, the routes above, and (if `frontend/dist` exists) serves the built UI with a safe single-page-app fallback that blocks `../` path traversal.

## Smaller modules

- `errors.py`: the typed errors.
- `redact.py`: `scrub()` masks API keys in any text; `RedactingFilter` applies it to every log line.
- `ratelimit.py`: a sliding-window limiter.
- `providers.py`: creates the AI client; the base URL comes from config only.
- `samples.py`: the sample allow-list.
- `cli.py`: argument parsing, git diff reading, report writing.
