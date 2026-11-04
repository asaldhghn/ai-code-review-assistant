# 2 to 3 minute demo script

Before you start: backend and frontend running (or the hosted demo open), browser at the Workspace, Demo mode selected, window wide enough to show the results layout. Have `screenshots/results.png` as a fallback.

## 0:00 · The problem (20 s)

"Code review catches bugs and security holes, but it is slow and reviewers get tired. I built a tool that gives a first pass: it reads code and explains each problem, why it matters and how to fix it. It started as a university assignment, a command-line AI reviewer, and I turned it into a full-stack product."

## 0:20 · The demo (70 s)

1. "I'll load a sample with some deliberately bad Python." Choose **Python: user service**. Point at the line numbers.
2. "This is Demo mode, shown in the corner. It is a rule-based scanner, not AI, so you can try it without an API key. With a key I switch to Live AI." Click **Run review**.
3. "Ten findings. The summary and the bar are computed from the real results." Click **Critical** in the severity filter, then **Security**.
4. Open "SQL built from string concatenation." "What is wrong, why it matters, suggested fix. The dot in the code view marks the exact line."
5. Click **Export HTML**, or **Export JSON**. "Reports are generated from validated data and escaped, so reviewed code cannot inject script into them."

## 1:30 · How it works (45 s)

"The React frontend calls a FastAPI backend. For live reviews, two reviewers run concurrently, each with its own prompt. They must answer in a strict JSON schema. I validate the reply, retry once if it is malformed, and discard findings that point at files or lines that do not exist. If one reviewer fails, for example a rate limit, the other's results still come back as a partial result. The same engine powers the CLI, which can review staged git changes."

## 2:15 · One technical challenge (25 s)

"The hard part was trusting model output. Models invent line numbers and sometimes return broken JSON, so I treat the response like untrusted input: schema, validation, retry, then cleanup. On the web path the model has no tools and no filesystem access, and code is never executed, so even a prompt injection in the pasted code has little to attack."

## 2:40 · Next (20 s)

"Tested with pytest, Vitest and Playwright, checked in GitHub Actions. I have not benchmarked the AI's accuracy, so next I would build a labeled set of vulnerable and clean files to measure it, add a judge pass to merge duplicate findings, and support reviewing a GitHub pull request by URL."

## Likely follow-ups

- *Why a demo mode?* So anyone can try it and a public deployment cannot spend money.
- *Is the demo mode AI?* No, and the app says so in the badge, banner, report and CLI.
- *What if the key is wrong?* A typed `invalid_credentials` error with a hint; the key is never logged.
- *Show me the code you are proudest of.* `clean_findings` in `agents.py`, or `test_agents.py` with the fake client.
