# Third-party notices

This project uses open-source software. Each package keeps its own license; the full texts ship inside the installed packages (`node_modules/<pkg>/LICENSE`, the package metadata for Python wheels).

## Fonts bundled in the built web app (SIL Open Font License 1.1)

- **Inter**, Copyright 2016 The Inter Project Authors (https://github.com/rsms/inter), via `@fontsource-variable/inter`.
- **JetBrains Mono**, Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono), via `@fontsource-variable/jetbrains-mono`.

License text: https://openfontlicense.org (OFL 1.1). The fonts are used unmodified.

## Runtime dependencies (summary)

| Ecosystem | Packages | License |
| --- | --- | --- |
| Python | FastAPI, Pydantic, Starlette, anyio, h11 | MIT |
| Python | uvicorn, httpx, httpcore, python-dotenv, click, idna | BSD-3-Clause |
| Python | openai (SDK) | Apache-2.0 |
| Python | typing-extensions | PSF-2.0 |
| Python | certifi, tqdm | MPL-2.0 (tqdm: MPL-2.0 AND MIT); used unmodified |
| npm | react, react-dom, scheduler | MIT |
| npm | lucide-react | ISC |

Development-only tools (Vite, Tailwind CSS, Vitest, Playwright, ESLint, Ruff, pytest, axe-core and others) are not shipped in the Docker image. axe-core is MPL-2.0 and is used only in tests.

This list was generated from package metadata on 2026-11-04 and should be re-checked when dependencies change.
