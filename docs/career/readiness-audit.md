# Recruiter-readiness audit

Written from the point of view of a technical interviewer reading this repository. **Verified** means I ran a command and saw the result (listed in the last section). **Judgment** means my opinion, which you should check yourself. No score here guarantees an interview or an offer.

## Summary

| Area | Verdict | Basis |
| --- | --- | --- |
| Functionality | Good for an MVP | Verified: demo flow, filters, export, errors, CLI. Not verified: live AI against a real provider |
| Code quality | Good | Verified: lint and types clean. Judgment: readable, but `agents.py` and `demo.py` are long |
| Architecture | Good | Judgment: clear layers; one engine shared by API and CLI |
| Security | Solid for scope | Verified by tests and audits (below). Not independently reviewed by a person |
| UI/UX | Strong | Judgment from screenshots; axe scans pass. No usability testing with real users |
| Accessibility | Partly verified | Verified: axe-core WCAG A/AA scans of 4 screens, keyboard flow test. Not done: screen-reader testing |
| Testing | Strong | Verified counts; no coverage percentage measured |
| Documentation | Strong | Judgment; every README command was run, except Docker |
| GitHub presentation | Incomplete | Private; no license; no live URL |
| Interview readiness | Depends on you | See [co-op-readiness-checklist.md](co-op-readiness-checklist.md) |
| Deployment safety | Verified locally | Docker container tested; live AI cannot be triggered ([../deployment.md](../deployment.md)) |

## Weaknesses (honest list)

1. **Not deployed.** There is no live URL, so a recruiter cannot try it in 10 seconds. The Docker image was built and tested locally, and the Render setup is documented in [../deployment.md](../deployment.md), but nothing is running on Render yet.
2. **Live AI never exercised with a real key.** Verified with a fake client and with the real OpenAI SDK against a mocked HTTP transport, but not against OpenRouter. Default model ids come from the course assignment and may be wrong for your provider.
3. **AI finding quality is unmeasured.** No labeled benchmark. Claims about "finding problems" apply to the demo rules (tested) and not to model accuracy.
4. **Demo scanner is shallow.** About 20 rules; the "magic number" rule can be noisy and none of it understands data flow. It is labeled as such.
5. **Rate limiter** is in-memory, per process, and keys on the connecting address (a proxy would hide real clients). Acceptable for the demo-only deployment where live AI is off.
6. **No license** and the repo is private, so it is not yet usable as a portfolio link. Dependencies are MIT-compatible, but whether Seneca/AIP444 allows publishing the coursework-derived code is unconfirmed; see [../licensing-review.md](../licensing-review.md).
7. **Thin commit history** (a handful of large commits because the project was assembled in one session). It is honest, and should not be padded. Earlier commits carry a `Co-Authored-By: Claude` trailer; history was not rewritten, and later commits omit it as you requested.
8. **Mobile coverage is layout-level only.** Automated checks cover five viewport sizes in desktop Chromium with touch (no horizontal scroll, main flow works), but not real devices, Safari or Firefox. No light theme.
9. **Bleeding-edge dependency majors** (TypeScript 6, Vite 8, ESLint 10, Vitest 5). They work and CI passes, but a reviewer may be unfamiliar with them.
10. **The original "Judge" model stage was removed** from the assignment design; a reviewer who knows the assignment may ask why.

## Fixed during this audit

- axe-core found three real accessibility defects (line-number contrast, two accessible names that omitted their visible text). Fixed and covered by tests.
- Tapping a finding on a phone did not bring its details into view. Fixed.
- Added a test of the real OpenAI SDK over HTTP (request URL, auth header, strict schema, error mapping).

## Checks I ran (latest local run)

| Check | Result |
| --- | --- |
| `pytest -q` (backend) | 161 passed |
| `ruff check` and `ruff format --check` | clean |
| `npm run lint`, `npm run typecheck` | clean |
| `npm test` (Vitest) | 25 passed |
| `npm run build` | succeeds |
| `npm run e2e` (Playwright: smoke, axe accessibility, 5 viewport sizes) | 16 passed (1 screenshot script skipped by design) |
| Same Playwright suite against the running Docker container | 14 passed; the 2 tests that need live mode are skipped because the container correctly disables it |
| `docker build` and `docker run` (non-root user, `PORT` honored) | works; `/api/health` OK; live request with a header key returned HTTP 403 |
| gitleaks over all 8 commits | 12 hits, all fake test-fixture keys (`sk-live-abcdef123456` etc.); allowlisted in `.gitleaks.toml`; a realistic key is still detected (negative control) |
| Regex search of all history for key shapes, private keys, `.env`/`.pem` files | only fake fixtures; only `.env.example` committed |
| `pip-audit -r requirements.txt` | no known vulnerabilities |
| `npm audit --omit=dev` | 0 vulnerabilities |
| `npm audit` (all) | 1 moderate advisory in `minimatch`, pulled in by ESLint tooling; dev-only, not in the shipped bundle |
| Search for committed secrets | only obvious fake test fixtures |
| GitHub Actions | see the Actions tab; the run for each pushed commit is checked after pushing |

## Fixed in the final-prep pass

- README, About page and learning guide said Node.js 20+, but the test runner needs 22.12+. Corrected, and declared in `package.json`.
- Added tests that prove a demo-only deployment cannot create an AI client, and that deployment files force live reviews off.
- Added `THIRD_PARTY_NOTICES.md` (the bundled fonts are OFL-licensed and need a notice).

## Best next steps for a co-op application

1. Run one real live review with your own key and fix the model ids if needed.
2. Connect Render using [../deployment.md](../deployment.md) and verify the URL yourself.
3. Confirm the coursework-publishing question, choose a license, then make the repo public (history has already been scanned).
4. Complete the hands-on checklist and rehearse the demo script.
5. Optional: a small labeled set of vulnerable and clean files to measure the AI reviewers' precision.
