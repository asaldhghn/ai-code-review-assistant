# 02 · Architecture

## The big picture

```text
Browser (React)  ──HTTP/JSON──►  FastAPI  ──►  service.py  ──►  agents.py  ──►  AI provider
                                    │                │
                                    │                └──►  demo.py (no AI)
                                    └──►  reports.py (HTML / JSON files)

Terminal  ──►  cli.py  ──►  the same agents / demo / reports
```

**Frontend** and **backend** are separate programs. The frontend is only HTML, CSS and JavaScript running in the browser. It cannot call an AI model safely (it would expose the key) and cannot read files on a server. The backend does the real work and exposes a small HTTP API.

## The API

| Method and path | What it does |
| --- | --- |
| `GET /api/health` | "Is the server alive?" |
| `GET /api/config` | Tells the UI the limits and whether live AI is allowed |
| `GET /api/samples`, `GET /api/samples/{id}` | Bundled sample files, chosen by id |
| `POST /api/review` | Run a review; returns a `ReviewResponse` |
| `POST /api/reports/{html\|json}` | Turn a `ReviewResponse` into a downloadable report |

The shape of every request and response is defined once, in [schemas.py](../../backend/code_review/schemas.py), with Pydantic. FastAPI uses those models to validate incoming JSON and to generate the interactive docs at `/api/docs`. The frontend mirrors them in [types.ts](../../frontend/src/types.ts).

## Data flow of one review (live mode)

1. The browser sends `{code, language, reviewers, mode: "live"}` to `POST /api/review`. The API key, if the user typed one, goes in the `X-Api-Key` header, not in the body.
2. [api.py](../../backend/code_review/api.py) checks the per-IP rate limit, then calls `run_review()` in [service.py](../../backend/code_review/service.py).
3. `service.py` validates the input (not empty, not binary, not too big) and checks that live reviews are enabled and a key exists.
4. It builds a `ReviewInput` and starts every selected reviewer **at the same time** with `asyncio.gather` ([agents.py](../../backend/code_review/agents.py)).
5. Each reviewer sends a system prompt (its personality and rules) plus the numbered code to the model and asks for JSON that matches a strict schema.
6. The reply is parsed and validated. If it is malformed, the reviewer asks once more. Findings that name unknown files, or lines that do not exist, are cleaned.
7. `assemble_response()` gives each finding an id (`S1`, `M2`, ...), counts them by severity and reviewer, and records each reviewer's status.
8. If **every** reviewer failed, the most useful error is raised (for example "invalid API key"). If only one failed, the result is returned with `status: "partial"`.
9. The frontend shows the result.

Demo mode skips steps 4 to 6 and calls `run_demo_reviewer()` instead.

## Error handling

All errors are subclasses of `ReviewError` in [errors.py](../../backend/code_review/errors.py). Each has a stable `code` (like `rate_limited`), an HTTP status, and a message that is safe to show. One exception handler in `api.py` turns them into the same JSON shape:

```json
{ "error": { "code": "rate_limited", "message": "The AI provider rate limit was reached..." } }
```

Unexpected exceptions become a generic `internal_error`; the real traceback only goes to the server log.

## Why these design choices

- **No database.** Reviews are computed on request and returned. Nothing needs to persist for an MVP, so there is nothing to secure or migrate.
- **Shared code for web and CLI.** The CLI and API call the same agents, so a fix helps both.
- **Tools only in the CLI.** The AI can call `read_file` and `ripgrep` to look around a repository. That is fine on your own machine and dangerous on a public server, so the web path runs with tools off.
- **A fake AI client in tests.** Tests replace the OpenAI client with a scripted object, so they are fast, free and deterministic.
- **One container for deployment.** FastAPI serves the built frontend files too, so a host only runs one process.
