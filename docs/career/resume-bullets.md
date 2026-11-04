# Resume bullets

Pick one. All three are true of the current code; none claims users, performance gains or business impact.

**Option 1: full-stack focus**
- Built a full-stack AI code review tool (FastAPI, React, TypeScript, Tailwind) that returns structured security and maintainability findings with severity, line numbers and suggested fixes, with filterable results and HTML/JSON report export.

**Option 2: AI integration and security focus**
- Designed an LLM review pipeline with strict JSON-schema output, Pydantic validation, one-shot retry on malformed replies and line-number verification, plus typed error handling for rate limits, bad credentials and provider outages; added a rule-based demo mode so the app runs with no API key or cost.

**Option 3: quality and engineering practice focus**
- Built a tested, CI-checked web service and CLI: 150+ pytest tests with a faked AI client, Vitest component tests, Playwright end-to-end tests, Ruff/ESLint/TypeScript checks in GitHub Actions, and security controls including path-traversal protection, secret redaction, escaped reports and request rate limiting.

Numbers above are the counts at the last local run (157 backend, 25 frontend, 11 end-to-end). Update them if the suite changes.
