# 07 · Git and GitHub

## Concepts

- **Repository (repo)**: a project folder plus its full history, stored in a hidden `.git` folder.
- **Commit**: a saved snapshot with a message. Commits form a chain, so you can see and undo what changed.
- **Branch**: a movable label on a commit. `main` is the default line of work; you create other branches to try things safely.
- **Remote**: a copy of the repo on a server. `origin` is the usual name for the GitHub copy.
- **Push / pull**: send your commits to the remote / bring new ones down.
- **Pull request (PR)**: a proposal on GitHub to merge one branch into another, with review and automatic checks.

## The everyday cycle

```bash
git status                       # what changed?
git add backend/code_review/api.py
git commit -m "Reject oversized request bodies early"
git push
```

Good commit habits used in this project: one logical change per commit, a message that says *what and why*, and never committing secrets or generated files. The first commits here were "Add backend ..." and "Add React frontend ...".

## What stays out of the repo: `.gitignore`

[.gitignore](../../.gitignore) excludes `.env` (secrets), `.venv/` and `node_modules/` (huge, reinstallable), build output (`frontend/dist/`), and generated reports (`review-*.html`, which can contain someone's source code). `.env.example` is allowed because it only has placeholders.

**If a secret is ever committed**, deleting it in a later commit is not enough: it stays in history. You must revoke the key at the provider and then rewrite history. Never assume a pushed secret is private.

## Line endings

[.gitattributes](../../.gitattributes) sets `* text=auto eol=lf` so Windows and Linux contributors do not create noisy line-ending diffs.

## GitHub Actions (CI)

A **workflow** is a YAML file in `.github/workflows/` that GitHub runs on its servers when something happens. [ci.yml](../../.github/workflows/ci.yml) runs on every push to `main` and every pull request, with three jobs:

| Job | Steps |
| --- | --- |
| `backend` | install Python 3.12, `pip install -e ".[dev]"`, `ruff check`, `ruff format --check`, `pytest` |
| `frontend` | install Node 22, `npm ci`, lint, typecheck, Vitest, build |
| `e2e` | after the other two: build the UI, install Chromium, run Playwright |

`npm ci` installs exactly what `package-lock.json` says (reproducible), unlike `npm install`, which may update it. A red X on a commit means a check failed; click it to read the log.

Why CI matters: it proves the project builds on a clean machine (not just yours) and stops broken code from being merged unnoticed.

## Safe habits

- Check `git remote -v` before pushing, so you know where it goes.
- Do not force-push (`--force`) shared history.
- Use a branch and pull request for risky changes, even when working alone; it gives CI a chance to run first.
- Read `git diff --staged` before committing. (This project's CLI can review exactly that.)

## Try it with this project's CLI

```bash
git add some_file.py
code-review --reviewers security      # reviews your staged changes
```
