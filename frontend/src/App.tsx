import { useEffect, useState } from "react";
import { getConfig, getSamples } from "./api";
import { About } from "./components/About";
import { Header, type Page } from "./components/Header";
import { ResultsView } from "./components/results/ResultsView";
import { Workspace } from "./components/Workspace";
import { useReviewSession } from "./hooks/useReviewSession";
import type { AppConfig, SampleSummary } from "./types";

function pageFromHash(): Page {
  return window.location.hash.startsWith("#/about") ? "about" : "workspace";
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [samples, setSamples] = useState<SampleSummary[]>([]);
  const session = useReviewSession(config);

  useEffect(() => {
    const onHashChange = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // Config and samples are optional extras: the app still works (with defaults) if they fail to load.
  useEffect(() => {
    let cancelled = false;
    Promise.all([getConfig(), getSamples()])
      .then(([cfg, list]) => {
        if (cancelled) return;
        setConfig(cfg);
        setSamples(list);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    document.title = page === "about" ? "About · AI Code Review Assistant" : "AI Code Review Assistant";
  }, [page]);

  const showResults = page === "workspace" && session.view === "results" && session.result !== null;

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-ink"
      >
        Skip to content
      </a>
      <Header page={page} mode={showResults && session.result ? session.result.review.mode : session.mode} />
      <main id="main" tabIndex={-1} className="flex-1">
        {page === "about" ? (
          <About />
        ) : showResults && session.result ? (
          <ResultsView
            key={session.result.review.review_id}
            result={session.result}
            onEdit={() => session.setView("edit")}
          />
        ) : (
          <Workspace session={session} config={config} samples={samples} hasResult={session.result !== null} />
        )}
      </main>
      <footer className="border-t border-line px-4 py-5 text-center text-xs text-muted sm:px-6">
        AI Code Review Assistant{config ? ` v${config.version}` : ""} · Code is never executed · Demo mode is rule-based, not AI
      </footer>
    </div>
  );
}
