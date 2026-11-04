# 08 · Running the project

Requirements: **Python 3.12+**, **Node.js 20+**, **Git**. Optional: [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) for the CLI's AI search tool; Docker for the container.

## 1. Get the code

```bash
git clone <your repository URL>
cd ai-code-review-assistant
```

## 2. Start the backend

Windows PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn code_review.api:app_factory --factory --reload --port 8000
```

macOS / Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn code_review.api:app_factory --factory --reload --port 8000
```

Check it: open <http://127.0.0.1:8000/api/health> (should show `{"status":"ok",...}`) and <http://127.0.0.1:8000/api/docs> (interactive API docs).

A *virtual environment* (`.venv`) is a private copy of Python packages for this project. `--reload` restarts the server when you edit code. `--factory` tells uvicorn that `app_factory` is a function that builds the app.

## 3. Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite forwards `/api/...` calls to port 8000 (see `vite.config.ts`), so both must be running.

## 4. Try it

1. Pick **Load a sample... > Python: user service**.
2. Press **Run review**. You are in Demo mode: no key needed.
3. Click findings, use the filters, press **Export HTML**.

## 5. Single-process mode (UI served by the backend)

```bash
cd frontend && npm run build
cd ../backend && uvicorn code_review.api:app_factory --factory --port 8000
# open http://127.0.0.1:8000
```

## 6. Live AI reviews (optional, uses your own key)

1. Create an account with an OpenAI-compatible provider (default: OpenRouter) and an API key.
2. Copy `.env.example` to `backend/.env` and set `LLM_API_KEY=...`. Never commit this file.
3. Restart the backend. In the app choose **Live AI** (the key box is optional when the server has one), or paste a key in the box instead.
4. If your provider uses different model names, set `REVIEW_MODEL` in `.env`.

Live reviews send your code to the provider and may cost money.

## 7. The command line

```bash
cd backend && pip install -e .         # already done in step 2
code-review --demo --file code_review/sample_files/user_service.py
code-review --demo --file app.py --format json --output review.json
code-review --file app.py              # live AI, needs LLM_API_KEY
code-review                            # staged git changes of the current repo
```

If `code-review` is not found, use `python -m code_review ...` with the virtual environment active.

## 8. Run the checks

```bash
cd backend  && pytest -q && ruff check . && ruff format --check .
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
cd frontend && npx playwright install chromium && npm run e2e
```

On Windows, if Playwright cannot find Python, set `E2E_PYTHON` to your venv's `python.exe` path first.

## 9. Docker (demo-only image)

```bash
docker build -t code-review-demo .
docker run -p 8000:8000 code-review-demo     # http://localhost:8000, live AI disabled
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| UI says it could not reach the server | Start the backend (step 2) and use the dev URL from step 3 |
| `ModuleNotFoundError: code_review` | Activate the venv and run `pip install -e ".[dev]"` inside `backend/` |
| PowerShell blocks `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| "No API key available" | Use Demo mode, or set `LLM_API_KEY` / paste a key |
| "Live AI reviews are disabled" | The server has `ENABLE_LIVE_REVIEW=false`; set it to `true` locally |
| CLI: "ripgrep ... not installed" | Install `rg`, or pass `--no-tools` |
