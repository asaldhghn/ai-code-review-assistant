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

## Weaknesses (honest list)

1. **Not deployed.** There is no live URL. A recruiter cannot try it in 10 seconds. The Dockerfile and `render.yaml` exist but the image has **not been built** (no Docker on the development machine).
2. **Live AI never exercised with a real key.** Verified with a fake client and with the real OpenAI SDK against a mocked HTTP transport, but not against OpenRouter. Default model ids come from the course assignment and may be wrong for your provider.
3. **AI finding quality is unmeasured.** No labeled benchmark. Claims about "finding problems" apply to the demo rules (tested) and not to model accuracy.
4. **Demo scanner is shallow.** About 20 rules; the "magic number" rule can be noisy and none of it understands data flow. It is labeled as such.
5. **Rate limiter** is in-memory, per process, and keys on the connecting address (a proxy would hide real clients). Acceptable for the demo-only deployment where live AI is off.
6. **No license** and the repo is private, so it is not yet usable as a portfolio link.
7. **Thin commit history** (a handful of large commits because the project was assembled in one session). It is honest, and should not be padded. Earlier commits carry a `Co-Authored-By: Claude` trailer; history was not rewritten, and later commits omit it as you requested.
8. **Frontend untested at real mobile widths in e2e** (only layout screenshots were checked manually) and no light theme.
9. **Bleeding-edge dependency majors** (TypeScript 6, Vite 8, ESLint 10, Vitest 5). They work and CI passes, but a reviewer may be unfamiliar with them.
10. **The original "Judge" model stage was removed** from the assignment design; a reviewer who knows the assignment may ask why.

## Fixed during this audit

- axe-core found three real accessibility defects (line-number contrast, two accessible names that omitted their visible text). Fixed and covered by tests.
- Tapping a finding on a phone did not bring its details into view. Fixed.
- Added a test of the real OpenAI SDK over HTTP (request URL, auth header, strict schema, error mapping).

## Checks I ran (latest local run)

| Check | Result |
| --- | --- |
| `pytest -q` (backend) | 157 passed |
| `ruff check` and `ruff format --check` | clean |
| `npm run lint`, `npm run typecheck` | clean |
| `npm test` (Vitest) | 25 passed |
| `npm run build` | succeeds |
| `npm run e2e` (Playwright, 11 tests incl. axe) | 11 passed |
| `pip-audit -r requirements.txt` | no known vulnerabilities |
| `npm audit --omit=dev` | 0 vulnerabilities |
| `npm audit` (all) | 1 moderate advisory in `minimatch`, pulled in by ESLint tooling; dev-only, not in the shipped bundle |
| Search for committed secrets | only obvious fake test fixtures |
| GitHub Actions | see the Actions tab; the run for each pushed commit is checked after pushing |

## Best next steps for a co-op application

1. Run one real live review with your own key and fix the model ids if needed.
2. Deploy the demo-only image and verify the URL yourself.
3. Choose a license, scan history for secrets, then make the repo public.
4. Complete the hands-on checklist and rehearse the demo script.
5. Optional: a small labeled set of vulnerable and clean files to measure the AI reviewers' precision.
