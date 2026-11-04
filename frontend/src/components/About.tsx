import { Cpu, FlaskConical, ListChecks, ShieldCheck, TerminalSquare, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

function Card({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-surface p-5">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <span className="text-accent">{icon}</span>
        {title}
      </h2>
      <div className="space-y-3 text-sm leading-relaxed text-fg/90">{children}</div>
    </section>
  );
}

function Code({ children, label }: { children: string; label: string }) {
  return (
    <pre
      aria-label={label}
      tabIndex={0}
      className="overflow-x-auto rounded-md border border-line bg-bg p-3 font-mono text-[12.5px] leading-5 text-fg"
    >
      {children}
    </pre>
  );
}

export function About() {
  return (
    <div className="mx-auto max-w-[1000px] space-y-5 px-4 py-8 sm:px-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">About AI Code Review Assistant</h1>
        <p className="mt-2 max-w-2xl text-muted">
          A developer tool that reviews source code for security vulnerabilities and maintainability problems, and
          explains each finding with why it matters and how to fix it.
        </p>
      </header>

      <div className="grid gap-5 md:grid-cols-2">
        <Card icon={<ListChecks aria-hidden="true" className="size-5" />} title="What it does">
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              Two reviewers run side by side: a <strong>Security Auditor</strong> (secrets, injection, unsafe calls, weak
              crypto) and a <strong>Maintainability Critic</strong> (naming, duplication, dead code, error handling).
            </li>
            <li>
              Each finding has a severity, a file and line, an explanation, why it matters, and a suggested improvement.
            </li>
            <li>Filter results by severity and reviewer, click a finding to jump to its line, and export a report.</li>
            <li>The same engine is available from the command line for files and staged git changes.</li>
          </ul>
        </Card>

        <Card icon={<Cpu aria-hidden="true" className="size-5" />} title="How a review works">
          <ol className="list-decimal space-y-1.5 pl-5">
            <li>Your code is sent to the API (it is never executed, only read as text).</li>
            <li>
              Each selected reviewer gets its own prompt and must answer in a strict JSON schema, so output is structured
              data rather than free text.
            </li>
            <li>
              Responses are validated. Findings that name files outside the review, or lines that do not exist, are
              discarded or shown without a line number.
            </li>
            <li>The results are merged into one summary with counts by severity and by reviewer.</li>
          </ol>
        </Card>

        <Card icon={<FlaskConical aria-hidden="true" className="size-5" />} title="Demo mode vs Live AI">
          <p>
            <strong>Demo mode</strong> needs no account or API key. It uses a deterministic scanner with fixed regex rules
            (plus Python <code>ast</code> checks) and always shows a &ldquo;Demo&rdquo; label. It is{" "}
            <strong>not an AI review</strong>: it finds well-known patterns like hardcoded secrets, SQL built from strings,
            <code> eval</code>, unused imports and duplicated functions, and it misses everything else.
          </p>
          <p>
            <strong>Live AI</strong> sends your code to an OpenAI-compatible provider (OpenRouter by default) using your
            own API key and returns the model&rsquo;s findings. It is disabled on the public demo so no one can spend
            money through it.
          </p>
        </Card>

        <Card icon={<ShieldCheck aria-hidden="true" className="size-5" />} title="Security & privacy">
          <ul className="list-disc space-y-1.5 pl-5">
            <li>Submitted code is never executed, and the web API has no access to the server&rsquo;s filesystem.</li>
            <li>Your API key is sent only with the request that needs it, is not stored, and is redacted from logs.</li>
            <li>Reports are generated with all content escaped, so reviewed code cannot inject script into them.</li>
            <li>In Live AI mode your code is sent to the AI provider. Do not paste code you are not allowed to share.</li>
          </ul>
        </Card>
      </div>

      <Card icon={<TriangleAlert aria-hidden="true" className="size-5" />} title="Limitations">
        <ul className="list-disc space-y-1.5 pl-5">
          <li>AI reviewers can miss real problems and can report false positives. Treat findings as review comments, not verdicts.</li>
          <li>Each review looks at one pasted file or snippet, so cross-file issues are out of reach in the web app.</li>
          <li>Input is limited to 60,000 characters by default; very large files should be reviewed in parts.</li>
          <li>The demo scanner only knows a short list of patterns and has no semantic understanding of your code.</li>
          <li>Results are not saved: closing the page discards them, so export what you want to keep.</li>
        </ul>
      </Card>

      <Card icon={<TerminalSquare aria-hidden="true" className="size-5" />} title="Run it locally">
        <p>Requires Python 3.12+ and Node.js 22.12+.</p>
        <Code label="Backend setup commands">{`cd backend
python -m venv .venv
.venv\\Scripts\\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn code_review.api:app_factory --factory --reload --port 8000`}</Code>
        <Code label="Frontend setup commands">{`cd frontend
npm install
npm run dev                      # http://localhost:5173`}</Code>
        <Code label="Command line examples">{`code-review --demo --file app.py       # no API key needed
code-review --file app.py              # AI review (needs LLM_API_KEY)
code-review                            # review staged git changes
code-review --file app.py --format json --output review.json`}</Code>
        <p>
          For live AI reviews copy <code>.env.example</code> to <code>.env</code> and set <code>LLM_API_KEY</code>, or
          paste a key into the app.
        </p>
      </Card>
    </div>
  );
}
