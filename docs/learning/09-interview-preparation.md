# 09 · Interview preparation

Answers are written so you can say them in your own words. Every claim matches the code; if you are unsure, open the file named in brackets before the interview.

## The project

**Q: Tell me about this project.**
It is a code review tool. You paste code or run it on staged git changes, and two reviewers, one for security and one for maintainability, return structured findings with an explanation and a suggested fix. It has a FastAPI backend, a React and TypeScript frontend, and a CLI. It started as my AIP444 assignment, which was a command-line AI reviewer; I turned it into a tested full-stack product.

**Q: What did you build yourself versus reuse?**
The reviewer prompts and the tool-calling loop came from my assignment. For this project I added the API, the web interface, the typed error system, the rule-based demo engine, report generation, rate limiting and the tests, and I extended the findings to include a title, why it matters and a suggested fix. I also removed the assignment's third "judge" model and generate reports deterministically instead. [README: "What changed"]

**Q: Why a demo mode?**
So anyone can try it without an account or paying for AI calls, and so a public deployment cannot be abused to spend my money. It is a different engine (regex rules plus Python `ast`), and every response, the UI, reports and the CLI label it as not AI. I did not want to present canned output as an AI result. [demo.py, `is_demo`]

## Architecture

**Q: Walk me through what happens when I click "Run review".**
The browser POSTs the code to `/api/review`. The route checks a per-IP rate limit for live mode, then `service.run_review` validates the input, picks the engine, and for live mode runs each reviewer concurrently with `asyncio.gather`. Each reviewer sends a system prompt and the numbered code, asks for JSON in a strict schema, validates the reply with Pydantic, retries once if it is malformed, and cleans the findings. The service assembles counts and statuses into a `ReviewResponse`, and the frontend renders it. [02-architecture.md]

**Q: Why FastAPI?**
It is async, which fits calling a slow external API from two reviewers at once; Pydantic models give request validation and typed responses; and it generates interactive API docs. The tests also use its `TestClient`.

**Q: Why no database?**
Nothing has to persist in the MVP: a review is computed and returned. Adding a database would add migrations, security and hosting cost without a feature that needs it. History is on the roadmap and would be the reason to add one.

**Q: How do you share code between the CLI and the API?**
Both call the same agents, schemas, demo engine and report functions. Only the entry points differ: `api.py` and `cli.py`.

## AI engineering

**Q: How do you make sure the model returns usable output?**
Four layers: a strict JSON schema in the request, Pydantic validation of the reply, one retry that feeds the validation error back, and a cleanup step that discards findings for files that are not in the review and clears line numbers that do not exist. Failure after the retry becomes a typed error rather than a crash. [agents.py: `parse_result`, `_final_result`, `clean_findings`]

**Q: What about prompt injection?**
The code under review is attacker-controlled text. The prompts say that code, comments and tool output are untrusted data and must never be followed as instructions. Also, the model has no dangerous capability to abuse on the web path: no tools, no code execution, and the output is escaped before display. I did not claim it is immune; it reduces the risk, and the harm ceiling is low by design.

**Q: What are the tools and why are they CLI-only?**
`read_file` and `ripgrep` let the model look at other files in the repository when judging a change. On my laptop, restricted to the repo, that is useful. On a public server it would expose the filesystem, so the web path runs with tools off. The tools also block `.env`, keys, `.git` and symlink escapes. [tools.py, test_tools_security.py]

**Q: How do you handle provider failures and cost?**
Errors are translated into typed errors with stable codes: invalid key, rate limit, unavailable, bad response. If one reviewer fails the other's result is still returned as a partial result. Cost is bounded by an input size limit, max tokens, bounded tool rounds, a timeout, a per-IP rate limit, and `ENABLE_LIVE_REVIEW=false` for public hosting.

**Q: How do you know the AI part works?**
Honest answer: the tests use a scripted fake client, so they verify my handling of replies, retries, errors and tools, not the model's judgment. I have not measured finding quality with a benchmark. A natural next step would be a small labeled set of vulnerable and clean files to measure precision and recall.

## Security

**Q: What security measures did you add?**
Code is never executed; the API has no filesystem access (samples come from an id allow-list); keys are never stored and are scrubbed from logs and errors; the provider URL is server-side only; reports escape every value and carry a CSP; there are limits on input, body size, time and request rate; and security headers on responses. There are tests for path traversal, report injection and secret leakage. [03-backend.md, test_api.py]

**Q: What is a vulnerability you deliberately avoided?**
SSRF: if the client could choose the AI base URL, the server could be made to call internal addresses. It is read from server configuration only. Another is XSS in the report: model output goes through `html.escape`, and in React I render inline code as elements, never `innerHTML`.

**Q: What are the weak spots?**
The rate limiter is in-memory and per process, and behind a proxy it needs the real client address. The API key is typed into a web form, which is fine on localhost but is why the public demo disables live mode.

## Frontend

**Q: How is state managed?**
`useState` plus one custom hook, `useReviewSession`, for the workspace. I avoided a state library because the state is small. Selection in the results is derived from filters instead of synced with an effect, which removed a class of bugs.

**Q: How did you handle accessibility?**
Semantic HTML, labeled inputs, visible focus, `aria-pressed` on filters, severity shown with icon and text instead of color alone, a skip link, a text alternative for the severity chart, and reduced-motion support. I have not run a full audit with a screen reader.

## Testing

**Q: What is your testing strategy?**
Fast unit and API tests for the backend with a fake AI client, component tests for the frontend with a mocked `fetch` and simulated user input, and a few Playwright tests against the real stack. CI runs lint, types, tests and build on every push. I do not quote a coverage number because I did not measure one.

**Q: Describe a bug a test caught or a decision a test forced.**
When I first ran the demo scanner on the sample file, it reported a "magic number" inside a fake API key string. Rules should not match inside string literals, so I added a `code_only` option that blanks string contents before matching, and added tests that eval-like text and long numbers inside strings produce no findings. A second example: an ESLint React rule rejected my first way of forcing demo mode on demo-only servers, and the fix (deriving the value instead of syncing it in an effect) was simpler.

## Challenges and growth

**Q: What was the hardest part?**
Making AI output trustworthy enough to display: lines that do not exist, files that were never in the review, malformed JSON. The fix was treating the model as an unreliable input source and validating everything. Second was designing a demo mode that is useful but honest about not being AI.

**Q: What would you do next?**
Add a judge pass to de-duplicate overlapping findings across reviewers, support reviewing a GitHub pull request by URL, measure quality on a labeled set, and add streaming progress for long reviews.

**Q: What would you change if this had 10,000 users?**
Move rate limiting to a shared store such as Redis, add authentication and per-user quotas, queue reviews in background workers, cache by code hash, and add structured logging and metrics.
