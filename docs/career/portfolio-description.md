# Portfolio description

## One sentence

AI Code Review Assistant reviews source code for security and maintainability problems and explains each finding with why it matters and how to fix it, through a React web app, a FastAPI backend and a CLI.

## Portfolio card (short)

A full-stack code review tool. Paste code or review staged git changes; two reviewers return structured findings with severity, line, explanation and a suggested fix. Try the no-key demo mode, or bring your own API key for real AI reviews. Python, FastAPI, React, TypeScript.

## Detailed description

AI Code Review Assistant grew out of a university assignment: a command-line tool that asked two AI reviewers, a Security Auditor and a Maintainability Critic, to review staged git changes. I kept that core and turned it into a complete product: a typed FastAPI service, a responsive React interface, a CLI, report export, and a test suite.

Users paste code, load a sample or upload a file, pick the reviewers and run a review. The results screen shows summary counts, a severity distribution, filters by severity and reviewer, a detail panel for each finding (what is wrong, why it matters, suggested improvement) and a code view that marks the affected lines. Reports export as self-contained HTML or JSON.

There are two engines. Live AI mode calls any OpenAI-compatible provider with the user's own API key and requires structured JSON output that is validated before display. Demo mode is a deterministic rule-based scanner (regex rules and Python `ast` checks) that needs no credentials; it is labeled as not AI everywhere it appears, so it cannot be mistaken for a model's work. The public deployment is intended to be demo-only so that no one can spend money through it.

## Technology

Python 3.12, FastAPI, Pydantic v2, OpenAI SDK (OpenRouter by default), pytest · React 19, TypeScript, Vite, Tailwind CSS v4, Vitest, Testing Library, Playwright · Ruff, ESLint, GitHub Actions, Docker.

## Main technical challenges

- **Trusting model output.** Replies must match a JSON schema, are validated and retried once, and findings that cite files or lines that do not exist are discarded or have the line removed.
- **Safe by default.** The web path has no filesystem tools and never executes code; the CLI's tools are confined to the repository root with secret-file and symlink protections; keys are redacted from logs and errors; reports escape all content.
- **Graceful failure.** Reviewers fail independently, so one rate-limited reviewer yields a partial result instead of an error. Provider failures map to typed, user-readable errors.
- **An honest demo.** Building a useful no-cost mode while labeling it clearly as rule-based, not AI.
- **Testing AI code without AI.** A scripted fake client makes the pipeline's retries, errors and tool loop deterministic and free to test.

## Lessons learned

- Treat model output as untrusted input and validate everything.
- Put limits (size, time, rate, tokens) in from the start; they are part of the design, not an afterthought.
- Deriving state beats syncing state: fewer effects, fewer bugs.
- Test behavior through public entry points (HTTP, user clicks) rather than internals.
- A tool that is fine on a developer's machine (filesystem access) can be unsafe when hosted, so separate those paths explicitly.
- I have not benchmarked AI finding quality; measuring it against labeled examples is the next thing I would do.
