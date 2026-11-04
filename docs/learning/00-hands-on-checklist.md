# Hands-on learning checklist

Reading is not understanding. Do each task yourself, without asking an AI to do it for you, and tick it only when you could explain it to an interviewer. Write short notes in your own words in a private file (not in the repo).

## 1. Run it independently
- [ ] Delete your `backend/.venv` and `frontend/node_modules`, then follow [08-running-the-project.md](08-running-the-project.md) from a fresh clone.
- [ ] Open `/api/docs` and `/api/health` in the browser. Run a demo review in the UI.
- [ ] Explain in your own words why the backend and the frontend are two separate processes in development.

## 2. Explain one API endpoint
- [ ] Pick `POST /api/review`. Open [api.py](../../backend/code_review/api.py) and [service.py](../../backend/code_review/service.py).
- [ ] Say what the request body is, what each field is validated against ([schemas.py](../../backend/code_review/schemas.py)), which errors it can return and their status codes.
- [ ] Call it with `curl` or the `/api/docs` page and read the JSON you get back.

## 3. Trace a request from the browser to the backend
- [ ] Open the browser dev tools Network tab, click **Run review**, and find the request.
- [ ] Follow it through: `Workspace.tsx` button, `useReviewSession.run`, `api.postReview`, `api.py` route, `service.run_review`, `demo.run_demo_reviewer`, back to `ResultsView`. Write one sentence per hop.

## 4. Explain the AI reviewer workflow
- [ ] Read [05-ai-integration.md](05-ai-integration.md) and [agents.py](../../backend/code_review/agents.py).
- [ ] Without looking, explain: the system prompt vs. the user message, why the output must match a JSON schema, what happens when the model returns bad JSON, what `clean_findings` removes, and why the web path has no tools.

## 5. Modify one small feature
- [ ] Add a demo rule in [demo.py](../../backend/code_review/demo.py), for example flag `time.sleep(` in Python as an `info` maintainability finding, with title, explanation, why it matters and suggestion.
- [ ] Add a test in `tests/test_demo.py` that proves the new rule fires on the right line and does not fire inside a comment.
- [ ] See your rule appear in the UI.

## 6. Run the tests
- [ ] Backend: `pytest -q`. Frontend: `npm test`. End-to-end: `npm run build` then `npm run e2e`.
- [ ] Say what each layer protects against that the others do not.

## 7. Debug a controlled error
- [ ] Break something on purpose: in `schemas.py` rename `why_it_matters` in `ApiFinding` to `why`. Run `pytest -q` and read the failures from the bottom up. Predict which tests fail before you run them.
- [ ] Revert it with `git restore backend/code_review/schemas.py`.
- [ ] Second exercise: start the backend with `MAX_CODE_CHARS=200` and paste a long file. Find where the 413 error is produced and where the UI shows it.

## 8. Explain one technical trade-off
Choose one and explain both sides, in a minute, out loud:
- [ ] Demo mode as rule-based code instead of canned sample output.
- [ ] No database (what you gain, what you give up).
- [ ] Tools enabled in the CLI but disabled in the web API.
- [ ] Deterministic report generation instead of a model writing the HTML.
- [ ] A plain `<textarea>` instead of a full code editor component.

## Final check
- [ ] You can answer at least 10 questions from [09-interview-preparation.md](09-interview-preparation.md) without reading the answers.
- [ ] You have read [../career/co-op-readiness-checklist.md](../career/co-op-readiness-checklist.md).
