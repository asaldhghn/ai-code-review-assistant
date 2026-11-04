import { FileUp, FlaskConical, LoaderCircle, Play, Sparkles, X } from "lucide-react";
import { useRef } from "react";
import { LANGUAGE_LABEL, REVIEWER_LABEL } from "../lib/findings";
import type { useReviewSession } from "../hooks/useReviewSession";
import type { AppConfig, ReviewerId, SampleSummary } from "../types";
import { CodeEditor } from "./CodeEditor";
import { ErrorBanner } from "./ErrorBanner";

type Session = ReturnType<typeof useReviewSession>;

interface Props {
  session: Session;
  config: AppConfig | null;
  samples: SampleSummary[];
  /** True when a previous result exists, so the user can jump back to it. */
  hasResult: boolean;
}

const REVIEWER_BLURB: Record<ReviewerId, string> = {
  security: "Secrets, injection, unsafe calls, weak crypto",
  maintainability: "Naming, duplication, dead code, error handling",
};

export function Workspace({ session, config, samples, hasResult }: Props) {
  const fileInput = useRef<HTMLInputElement>(null);
  const liveAllowed = config?.live_review_enabled ?? true;
  const keyOptional = config?.server_key_configured ?? false;
  const canRun = session.code.trim().length > 0 && session.reviewers.length > 0 && !session.loading;

  return (
    <div className="mx-auto grid max-w-[1400px] gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section aria-labelledby="editor-title" className="min-w-0">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 id="editor-title" className="text-lg font-semibold tracking-tight">
              Review your code
            </h1>
            <p className="text-sm text-muted">
              {session.filename ? (
                <>
                  <span className="font-mono text-fg">{session.filename}</span> ·{" "}
                </>
              ) : null}
              Paste code, load a sample, or upload a file.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="sample-select">
              Load a sample
            </label>
            <select
              id="sample-select"
              value=""
              onChange={(e) => e.target.value && void session.loadSample(e.target.value)}
              className="h-9 rounded-md border border-line-strong bg-raised px-2.5 text-sm text-fg hover:border-accent/50"
            >
              <option value="">Load a sample…</option>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>

            <input
              ref={fileInput}
              type="file"
              className="sr-only"
              tabIndex={-1}
              aria-label="Upload a source file"
              accept=".py,.js,.jsx,.mjs,.ts,.tsx,.java,.go,.cs,.cpp,.cc,.c,.h,.hpp,.rb,.php,.rs,.sql,.sh,.bash,.txt"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void session.loadFile(file);
                e.target.value = "";
              }}
            />
            <button type="button" onClick={() => fileInput.current?.click()} className={secondaryButton}>
              <FileUp aria-hidden="true" className="size-4" /> Upload file
            </button>
            <button
              type="button"
              onClick={session.clear}
              disabled={!session.code}
              className={secondaryButton}
            >
              <X aria-hidden="true" className="size-4" /> Clear
            </button>
          </div>
        </div>

        <CodeEditor
          value={session.code}
          onChange={session.setCode}
          onSubmit={() => void session.run()}
          maxChars={session.maxChars}
          disabled={session.loading}
        />
      </section>

      <aside aria-label="Review settings" className="space-y-5">
        <div className="space-y-5 rounded-md border border-line bg-surface p-4">
          <div>
            <label htmlFor="language" className="mb-1.5 block text-sm font-medium">
              Language
            </label>
            <select
              id="language"
              value={session.language}
              onChange={(e) => session.setLanguage(e.target.value)}
              className="h-9 w-full rounded-md border border-line-strong bg-raised px-2.5 text-sm"
            >
              {(config?.languages ?? Object.keys(LANGUAGE_LABEL)).map((l) => (
                <option key={l} value={l}>
                  {LANGUAGE_LABEL[l] ?? l}
                </option>
              ))}
            </select>
          </div>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium">Reviewers</legend>
            <div className="space-y-2">
              {(["security", "maintainability"] as ReviewerId[]).map((id) => (
                <label
                  key={id}
                  className="flex cursor-pointer items-start gap-2.5 rounded-md border border-line p-2.5 has-[:checked]:border-accent/50 has-[:checked]:bg-accent/5"
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 size-4 accent-[#2dd4bf]"
                    checked={session.reviewers.includes(id)}
                    onChange={() => session.toggleReviewer(id)}
                  />
                  <span>
                    <span className="block text-sm font-medium">{REVIEWER_LABEL[id]}</span>
                    <span className="block text-xs text-muted">{REVIEWER_BLURB[id]}</span>
                  </span>
                </label>
              ))}
            </div>
            {session.reviewers.length === 0 && (
              <p className="mt-1.5 text-xs text-crit">Select at least one reviewer.</p>
            )}
          </fieldset>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium">Review engine</legend>
            <div className="space-y-2">
              <label className="flex cursor-pointer items-start gap-2.5 rounded-md border border-line p-2.5 has-[:checked]:border-accent/50 has-[:checked]:bg-accent/5">
                <input
                  type="radio"
                  name="mode"
                  className="mt-0.5 size-4 accent-[#2dd4bf]"
                  checked={session.mode === "demo"}
                  onChange={() => session.setMode("demo")}
                />
                <span>
                  <span className="flex items-center gap-1.5 text-sm font-medium">
                    <FlaskConical aria-hidden="true" className="size-3.5 text-accent" /> Demo
                  </span>
                  <span className="block text-xs text-muted">
                    Deterministic rule-based scanner. No AI, no API key, no cost.
                  </span>
                </span>
              </label>
              <label
                className={`flex items-start gap-2.5 rounded-md border border-line p-2.5 has-[:checked]:border-info/50 has-[:checked]:bg-info/5 ${
                  liveAllowed ? "cursor-pointer" : "cursor-not-allowed opacity-60"
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  className="mt-0.5 size-4 accent-[#60a5fa]"
                  checked={session.mode === "live"}
                  disabled={!liveAllowed}
                  onChange={() => session.setMode("live")}
                />
                <span>
                  <span className="flex items-center gap-1.5 text-sm font-medium">
                    <Sparkles aria-hidden="true" className="size-3.5 text-info" /> Live AI
                  </span>
                  <span className="block text-xs text-muted">
                    {liveAllowed
                      ? "Sends your code to the configured AI provider using your API key."
                      : "Disabled on this public demo. Run the project locally with your own key."}
                  </span>
                </span>
              </label>
            </div>

            {session.mode === "live" && liveAllowed && (
              <div className="mt-3">
                <label htmlFor="api-key" className="mb-1.5 block text-sm font-medium">
                  API key {keyOptional && <span className="font-normal text-muted">(optional: server has one)</span>}
                </label>
                <input
                  id="api-key"
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  value={session.apiKey}
                  onChange={(e) => session.setApiKey(e.target.value)}
                  placeholder="sk-…"
                  className="h-9 w-full rounded-md border border-line-strong bg-raised px-2.5 font-mono text-sm placeholder:text-faint"
                  aria-describedby="key-help"
                />
                <p id="key-help" className="mt-1.5 text-xs text-muted">
                  Sent only with this request, kept in memory, never stored or logged.
                </p>
              </div>
            )}
          </fieldset>
        </div>

        {session.error && <ErrorBanner error={session.error} onDismiss={session.dismissError} />}

        <div className="space-y-2">
          {session.loading ? (
            <div className="space-y-2">
              <button
                type="button"
                disabled
                aria-busy="true"
                className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-accent/70 font-semibold text-accent-ink"
              >
                <LoaderCircle aria-hidden="true" className="spinner size-4" /> Reviewing…
              </button>
              <button type="button" onClick={session.cancel} className={`${secondaryButton} w-full justify-center`}>
                Cancel
              </button>
              <p role="status" className="text-center text-xs text-muted">
                {session.mode === "live" ? "Waiting for the AI reviewers. This can take up to a minute." : "Running the rule-based scanner…"}
              </p>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => void session.run()}
              disabled={!canRun}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-accent font-semibold text-accent-ink transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:bg-line disabled:text-faint"
            >
              <Play aria-hidden="true" className="size-4" /> Run review
            </button>
          )}
          {hasResult && !session.loading && (
            <button
              type="button"
              onClick={() => session.setView("results")}
              className={`${secondaryButton} w-full justify-center`}
            >
              Back to last results
            </button>
          )}
        </div>
      </aside>
    </div>
  );
}

export const secondaryButton =
  "inline-flex h-9 items-center gap-1.5 rounded-md border border-line-strong bg-raised px-3 text-sm font-medium text-fg transition-colors hover:border-accent/50 hover:text-accent-strong disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-line-strong disabled:hover:text-fg";
