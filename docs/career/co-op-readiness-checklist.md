# Co-op readiness checklist

Use this before you list the project on a resume or mention it in an interview. The goal is that everything you claim is something you can explain and defend.

## Be honest about how it was built

This project was developed with substantial AI assistance (Claude Code). The reviewer prompts and the first version of the agent loop are from your own AIP444 assignment. Interviewers commonly ask "what did you do yourself?" Decide your honest answer now, for example: *"The AI reviewer core is from my course assignment. I extended it into a web app with AI coding assistance, and I reviewed, ran, tested and can explain all of it."* Only say that last part once it is true. Do not claim authorship of code you cannot explain, and do not invent contributions.

## What is implemented (verified by tests or by running it)

- Pasted-code review in a React UI; language, reviewer and engine selection; sample loader; file upload.
- Demo mode: deterministic rule-based scanner, labeled as not AI.
- Live AI path: structured JSON output, validation, one retry, typed provider errors. Verified with a fake client and with the real OpenAI SDK against a mocked HTTP transport. **Not verified against a real provider with a real key** unless you do it yourself.
- Results: summary counts, severity bar, filters, detail view, code view, HTML and JSON export.
- CLI: `--file`, staged git diff, `--demo`, `--reviewers`, `--format`, `--output`, `--no-tools`, `--debug`.
- Security controls with tests: no code execution, no server filesystem access in the API, path-traversal and secret-file protection in CLI tools, key redaction, escaped reports, size/time/rate limits.
- Tests and CI: pytest, Vitest, Playwright (including axe accessibility scans), Ruff, ESLint, `tsc`, GitHub Actions.

## What is only planned (do not present as done)

Judge/consolidation pass, GitHub pull request review, saved history, streaming progress, SARIF export, benchmarking finding quality, hosted deployment (not deployed yet), full manual screen-reader audit.

## What you must personally be able to do

Tick these only after finishing [../learning/00-hands-on-checklist.md](../learning/00-hands-on-checklist.md).

- [ ] Clone, install and run the project from scratch without help.
- [ ] Draw the architecture on a whiteboard (browser, API, service, agents, provider, demo engine, reports).
- [ ] Trace one request end to end and name the files involved.
- [ ] Explain structured output, validation, retry and cleanup, and why each exists.
- [ ] Explain prompt injection and what the project does (and does not) do about it.
- [ ] Explain why tools are CLI-only and how path traversal is blocked.
- [ ] Explain what the fake AI client lets you test, and what it cannot tell you.
- [ ] Add a small feature and a test for it, live, on a screen share.
- [ ] Explain at least three trade-offs (no database, rule-based demo, textarea editor, in-memory rate limiter).
- [ ] State the known limitations without being asked.
- [ ] Run a real live review once with your own key (free tier or a small budget) so you can speak from experience, and note the result honestly.

## Before you apply

- [ ] README opens with the purpose and a screenshot; every command in it works on a clean clone.
- [ ] CI on `main` is green.
- [ ] Decide on and add a license (MIT is typical for portfolios), then make the repo public. Check history for secrets first.
- [ ] Deploy the demo-only version and verify the live URL yourself; add it to the README only after that.
- [ ] Resume bullets use only facts from the list above; update numbers if the test counts change.
- [ ] You can give the 2 to 3 minute demo from [interview-demo.md](interview-demo.md) without reading it.

## Questions to expect and where to prepare

Interview answers: [../learning/09-interview-preparation.md](../learning/09-interview-preparation.md). Vocabulary: [../learning/10-glossary.md](../learning/10-glossary.md).
