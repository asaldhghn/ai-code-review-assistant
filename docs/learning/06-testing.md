# 06 · Testing

Tests are programs that check other programs. There are three layers here, from small and fast to large and realistic.

## Layer 1: backend tests (pytest)

Run from `backend/`: `pytest -q` (154 tests, about 3 seconds).

| File | What it verifies |
| --- | --- |
| `test_schemas.py` | Finding normalization (`"HIGH"` to `critical`, `"7"` to `7`), required text, unknown fields rejected, request validators |
| `test_demo.py` | The rule engine: correct line numbers, determinism, sorted output, no false positives inside strings or comments, per-rule cap, syntax errors reported instead of crashing |
| `test_diffs.py` | Git diff parsing: added/context/deleted lines, renames, line verification |
| `test_agents.py` | The AI loop against a **fake client**: valid output, retry after malformed output, failure after two bad replies, each provider error type, one reviewer failing while the other succeeds, tool loop, forced tool call fallback, unknown tools blocked, bounded rounds |
| `test_tools_security.py` | `read_file` refuses `.env`, keys, `.git`, `../` traversal, absolute outside paths and symlink escapes |
| `test_service.py` | Input validation, demo labeling, live disabled, missing key, partial results, error priority, timeout |
| `test_api.py` | Every endpoint through HTTP: validation errors, 413 limits, key never echoed, rate limit, generic 500, report escaping, SPA path traversal |
| `test_cli.py` | CLI flows: demo reports, clear error messages, mocked live review, a real temporary git repo for staged-diff mode |
| `test_redact_and_ratelimit.py` | Secret masking and the limiter |

### The fake AI client

[tests/fakes.py](../../backend/tests/fakes.py) defines `FakeClient`, which looks like the OpenAI client but pops pre-written replies from a list (or raises a chosen exception). This makes tests free, offline and repeatable:

```python
client = FakeClient([status_error(openai.RateLimitError, 429)])
outcome = await run(client)
assert outcome.error.code == "rate_limited"
```

### Reading a test

```python
def test_html_report_escapes_untrusted_content(client):
    data = review(client).json()
    data["findings"][0]["title"] = "<script>alert(1)</script>"
    response = client.post("/api/reports/html", json=data)
    assert "<script>alert(1)" not in response.text
    assert "&lt;script&gt;" in response.text
```

Arrange (build data), act (call the API), assert (check behavior). It tests an outcome that matters (no script injection), not an implementation detail.

## Layer 2: frontend tests (Vitest + Testing Library)

Run from `frontend/`: `npm test` (25 tests). They render the real `<App />` in a simulated browser (jsdom), replace `fetch` with a mock, and use `userEvent` to click and type like a person:

- Run is disabled without code; the over-limit counter and error; at least one reviewer is required.
- Live mode asks for a key **before** any request is sent.
- Loading state, then results labeled as demo, with counts that match the data.
- Severity and reviewer filters, the "no match" empty state, and "Clear filters".
- Selecting a finding shows the explanation and fix.
- Empty result, partial result and API error states.
- Export calls the right endpoint; going back keeps the code.
- `api.test.ts`: the key is sent as a header only in live mode, error bodies become `ApiError`, network failure and cancel are reported.

Queries use accessible roles and names (`getByRole("button", {name: /run review/i})`), which also checks that the UI is usable with assistive technology.

## Layer 3: end-to-end tests (Playwright)

Run from `frontend/` after `npm run build`: `npm run e2e` (6 tests). Playwright starts the real FastAPI server, opens real Chromium, and drives the app: load a sample, run a demo review, filter to critical, open a SQL injection finding, export JSON and check the downloaded file, plus the empty state, the missing-key message, an injected server error, the About page and the keyboard shortcut. No AI provider is involved.

## Static checks

`ruff check` and `ruff format --check` for Python, ESLint and `tsc --noEmit` for TypeScript. They catch unused imports, type errors and React hook mistakes without running anything.

## What the tests do not cover

- Real AI model quality (the AI client is always faked).
- Visual appearance beyond what I checked in screenshots.
- Docker image build and any hosted deployment.
- No coverage percentage is claimed; I did not measure one.

## Commands cheat sheet

```bash
cd backend  && pytest -q && ruff check . && ruff format --check .
cd frontend && npm run lint && npm run typecheck && npm test && npm run build && npm run e2e
```
