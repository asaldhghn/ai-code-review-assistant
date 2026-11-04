# 10 · Glossary

Terms are explained in simple English, with where you can see them in this project.

| Term | Meaning |
| --- | --- |
| **API** | A set of URLs a program can call to get things done. Here: `/api/review`. |
| **Endpoint / route** | One URL plus method, such as `POST /api/review`. Defined in `api.py`. |
| **HTTP status code** | A number in the reply: 200 OK, 401 not authorized, 413 too large, 422 invalid input, 429 too many requests, 502 upstream failure, 500 server error. |
| **JSON** | A text format for data: `{"findings": []}`. The language of web APIs. |
| **Schema** | A description of what data must look like. Pydantic models are schemas. |
| **Pydantic** | A Python library that validates data against type-annotated models. |
| **FastAPI** | A Python web framework built on Pydantic and `async`. |
| **ASGI / uvicorn** | The server that runs a FastAPI app. `uvicorn code_review.api:app_factory --factory`. |
| **Async / await** | Code that can wait (for the network) without blocking other work. Lets both reviewers run at once. |
| **Environment variable** | A setting passed to a program from outside, like `LLM_API_KEY`. Keeps secrets out of code. |
| **`.env` file** | A local file of environment variables. Never committed. |
| **CORS** | A browser rule about which websites may call an API. Configured in `api.py` for the dev server. |
| **Middleware** | Code that runs on every request, such as the body-size check. |
| **Rate limiting** | Refusing too many requests from one client in a short time (`ratelimit.py`). |
| **SSRF** | Tricking a server into calling an address the attacker chooses. Avoided by fixing the AI URL in config. |
| **XSS** | Injecting script into a web page. Avoided by escaping content. |
| **SQL injection** | Building a SQL query from user text so the user can change the query. The demo scanner detects it. |
| **CSP** | Content-Security-Policy: a header or tag telling the browser what a page may load or run. |
| **Prompt** | Text instructions given to an AI model. |
| **System prompt** | The standing instructions (persona and rules), in `prompts/*.md`. |
| **Prompt injection** | Text in the input that tries to give the model new orders. Handled by treating input as untrusted data. |
| **Structured output** | Making a model answer in a strict format (JSON schema) so code can use it. |
| **Tool calling** | The model asking our program to run a function (`read_file`) and receive the result. |
| **Token** | A chunk of text a model reads or writes. Cost and limits are counted in tokens. |
| **LLM** | Large language model. |
| **OpenRouter** | A service offering many models behind one API key. The default provider. |
| **Reviewer / agent** | Here, one model call loop with its own prompt, focus and rules. |
| **Finding** | One reported problem with severity, location and explanation. |
| **Severity** | How serious: critical, warning, info. |
| **Diff** | The list of changes between two versions of files. `git diff --staged`. |
| **Staged changes** | Changes you marked with `git add` for the next commit. |
| **AST** | Abstract syntax tree: a structured view of code. Python's `ast` module powers some demo rules. |
| **Regex** | A pattern for matching text, e.g. `AKIA[0-9A-Z]{16}`. |
| **Virtual environment** | A private set of Python packages for one project (`.venv`). |
| **Dependency** | A library your project needs. Listed in `requirements.txt` and `package.json`. |
| **React** | A library for building user interfaces from components. |
| **Component** | A function returning part of the UI. |
| **Props** | Inputs passed into a component. |
| **State / hook** | Data that changes over time; `useState` and custom hooks manage it. |
| **TypeScript** | JavaScript with types, checked before running. |
| **Vite** | The tool that runs the dev server and builds the frontend. |
| **Tailwind CSS** | Styling with small utility classes in markup. |
| **Build** | Turning source into optimized files to deploy (`npm run build` creates `dist/`). |
| **SPA** | Single-page app: one HTML page whose JavaScript draws screens. |
| **Accessibility (a11y)** | Making the app usable with keyboard and assistive technology. |
| **ARIA** | HTML attributes that describe UI meaning to assistive technology (`aria-pressed`). |
| **Unit test** | Tests one small piece. |
| **Integration / API test** | Tests several pieces together through a real entry point. |
| **End-to-end (e2e) test** | Drives the whole app like a user, in a real browser (Playwright). |
| **Mock / fake** | A stand-in object used in tests (`FakeClient`). |
| **Lint** | Automatic checks for mistakes and style (Ruff, ESLint). |
| **CI** | Continuous integration: automatic checks on every push (GitHub Actions). |
| **Container / Docker** | A packaged runnable environment, built from a `Dockerfile`. |
| **Deployment** | Putting the app on a server so others can use it. |
| **Repository, commit, branch, remote** | See [07-git-and-github.md](07-git-and-github.md). |
