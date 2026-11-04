# 01 · Project overview

## What the app does

You give it source code. It gives you a list of problems, each explained in plain language: **what is wrong**, **why it matters**, and **how to fix it**. Two "reviewers" look at the code from different angles:

| Reviewer | Looks for | Example finding |
| --- | --- | --- |
| Security Auditor | Hardcoded secrets, SQL injection, `eval`, unsafe deserialization, disabled TLS checks | "SQL built from string concatenation" |
| Maintainability Critic | Vague names, duplicated code, unused imports, swallowed exceptions | "`price_with_tax_us` duplicates `price_with_tax_ca`" |

## Two engines

| | Demo mode | Live AI mode |
| --- | --- | --- |
| Who finds the problems | A fixed set of rules in [demo.py](../../backend/code_review/demo.py) | A language model, via an API |
| Needs an API key | No | Yes |
| Costs money | No | Yes (your key) |
| Same input, same output | Always | Not guaranteed |
| Labeled in the UI | "Demo mode, rule-based, no AI" | "Live AI" |

Demo mode exists so a recruiter can try the product without an account. It is **not** presented as AI: the API response has `is_demo: true`, and the UI, HTML report and CLI all say so.

## How a user interacts with it

1. Open the **Workspace**, paste code (or pick a sample, or upload a file).
2. Choose the language, which reviewers to run, and the engine (Demo or Live AI).
3. Press **Run review** (or `Ctrl+Enter`).
4. On the **Results** screen: read the summary, filter by severity or reviewer, click a finding to see the explanation and the marked line in the code, and export HTML or JSON.
5. The **About** page explains limitations and how to run it locally.

The same engine is available in a terminal:

```bash
code-review --demo --file app.py
```

## The pieces, in one sentence each

- `frontend/` is the website (React + TypeScript).
- `backend/code_review/api.py` is the web server that the website talks to.
- `backend/code_review/agents.py` is the code that talks to the AI model.
- `backend/code_review/demo.py` is the rule-based engine used for demo mode.
- `backend/code_review/cli.py` is the terminal version.
- `backend/tests/`, `frontend/src/**/*.test.*` and `frontend/e2e/` prove it works.

## Where this came from

The AI reviewers are from my AIP444 Assignment 1: a command-line tool that reviews staged git changes with two prompts and a tool-calling loop. This project keeps that core and adds an API, a web UI, a demo engine, reports and tests. The README's "What changed from the original assignment" section lists exactly what was kept, added and replaced.
