import { ArrowLeft, CircleCheck, Download, FileJson, Info, TriangleAlert } from "lucide-react";
import { useRef, useState } from "react";
import { ApiError, fetchReport } from "../../api";
import { filterFindings, hasActiveFilters, LANGUAGE_LABEL, NO_FILTERS, type FindingFilters } from "../../lib/findings";
import { downloadBlob, formatCount, formatTime } from "../../lib/format";
import type { ReportFormat } from "../../types";
import type { ReviewedResult } from "../../hooks/useReviewSession";
import { ModeBadge } from "../Badges";
import { ErrorBanner } from "../ErrorBanner";
import { secondaryButton } from "../Workspace";
import { CodeView } from "./CodeView";
import { FindingDetail } from "./FindingDetail";
import { FindingList } from "./FindingList";
import { Filters } from "./Filters";
import { Summary } from "./Summary";

interface Props {
  result: ReviewedResult;
  onEdit: () => void;
}

export function ResultsView({ result, onEdit }: Props) {
  const { review, code } = result;
  const [filters, setFilters] = useState<FindingFilters>(NO_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ReportFormat | null>(null);
  const [exportError, setExportError] = useState<ApiError | null>(null);
  const detailRef = useRef<HTMLDivElement>(null);

  // On narrow screens the detail panel sits below the list, so bring it into view after a pick.
  function selectFromList(id: string) {
    setSelectedId(id);
    if (window.matchMedia?.("(max-width: 1023px)").matches) {
      detailRef.current?.scrollIntoView?.({ block: "start" });
    }
  }

  const visible = filterFindings(review.findings, filters);
  // Derived selection: keep the user's pick while it is visible, otherwise fall back to the first.
  const activeId = visible.some((f) => f.id === selectedId) ? selectedId : (visible[0]?.id ?? null);
  const active = visible.find((f) => f.id === activeId);

  async function exportReport(format: ReportFormat) {
    setExporting(format);
    setExportError(null);
    try {
      const blob = await fetchReport(review, format);
      downloadBlob(blob, `review-${review.review_id}.${format}`);
    } catch (err) {
      setExportError(err instanceof ApiError ? err : new ApiError("The report could not be created.", "unknown"));
    } finally {
      setExporting(null);
    }
  }

  const notices = review.is_demo ? review.notices.filter((n) => !n.startsWith("Demo mode")) : review.notices;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button type="button" onClick={onEdit} className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-accent-strong">
            <ArrowLeft aria-hidden="true" className="size-4" /> Edit code
          </button>
          <h1 className="flex flex-wrap items-center gap-3 text-lg font-semibold tracking-tight">
            Review results <ModeBadge mode={review.mode} />
          </h1>
          <p className="mt-1 text-sm text-muted">
            <span className="font-mono text-fg">{review.filename}</span> · {LANGUAGE_LABEL[review.language] ?? review.language} ·{" "}
            {formatCount(review.line_count)} lines · {formatTime(review.created_at)} · review {review.review_id}
          </p>
        </div>

        <div className="flex flex-wrap gap-2" role="group" aria-label="Export report">
          <button type="button" className={secondaryButton} disabled={exporting !== null} onClick={() => void exportReport("html")}>
            <Download aria-hidden="true" className="size-4" /> {exporting === "html" ? "Exporting…" : "Export HTML"}
          </button>
          <button type="button" className={secondaryButton} disabled={exporting !== null} onClick={() => void exportReport("json")}>
            <FileJson aria-hidden="true" className="size-4" /> {exporting === "json" ? "Exporting…" : "Export JSON"}
          </button>
        </div>
      </div>

      {exportError && <ErrorBanner error={exportError} onDismiss={() => setExportError(null)} />}

      {review.is_demo && (
        <Notice tone="accent" icon={<Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />}>
          <strong>Demo results.</strong> These findings come from a deterministic rule-based scanner, not an AI model. Choose{" "}
          <em>Live AI</em> with your own API key for a real AI review.
        </Notice>
      )}
      {review.status === "partial" && (
        <Notice tone="warn" icon={<TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />}>
          <strong>Partial result.</strong> At least one reviewer failed, so some findings may be missing.
        </Notice>
      )}
      {notices.map((n) => (
        <Notice key={n} tone="muted" icon={<Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />}>
          {n}
        </Notice>
      ))}

      <Summary review={review} />

      {review.findings.length === 0 ? (
        <div className="rounded-md border border-line bg-surface p-8 text-center">
          <CircleCheck aria-hidden="true" className="mx-auto mb-3 size-8 text-ok" />
          <h2 className="text-base font-semibold">No findings reported</h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted">
            {review.is_demo
              ? "The rule-based demo scanner did not match any of its rules. That is not a guarantee the code is free of problems."
              : "The reviewers did not report any issues. That is not a guarantee the code is free of problems."}
          </p>
          <button type="button" onClick={onEdit} className={`${secondaryButton} mt-4`}>
            Review other code
          </button>
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
          <section aria-label="Findings list" className="min-w-0 space-y-3 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto lg:pr-1">
            <Filters findings={review.findings} filters={filters} onChange={setFilters} />
            <p className="text-xs text-muted" role="status">
              Showing {formatCount(visible.length)} of {formatCount(review.findings.length)} findings
            </p>
            {visible.length === 0 ? (
              <div className="rounded-md border border-dashed border-line-strong p-6 text-center text-sm">
                <p className="text-muted">No findings match these filters.</p>
                {hasActiveFilters(filters) && (
                  <button type="button" onClick={() => setFilters(NO_FILTERS)} className={`${secondaryButton} mt-3`}>
                    Clear filters
                  </button>
                )}
              </div>
            ) : (
              <FindingList findings={visible} selectedId={activeId} onSelect={selectFromList} />
            )}
          </section>

          <div ref={detailRef} className="min-w-0 scroll-mt-4 space-y-5">
            {active ? (
              <FindingDetail key={active.id} finding={active} />
            ) : (
              <div className="rounded-md border border-dashed border-line-strong p-8 text-center text-sm text-muted">
                Select a finding to see the explanation and suggested fix.
              </div>
            )}
            <CodeView code={code} findings={visible} selectedId={activeId} onSelect={setSelectedId} />
          </div>
        </div>
      )}
    </div>
  );
}

function Notice({ tone, icon, children }: { tone: "accent" | "warn" | "muted"; icon: React.ReactNode; children: React.ReactNode }) {
  const style = {
    accent: "border-accent/40 bg-accent/5 text-fg [&>svg]:text-accent",
    warn: "border-warn/40 bg-warn/10 text-fg [&>svg]:text-warn",
    muted: "border-line bg-surface text-muted",
  }[tone];
  return (
    <div role={tone === "warn" ? "alert" : "note"} className={`flex gap-2.5 rounded-md border p-3 text-sm ${style}`}>
      {icon}
      <div>{children}</div>
    </div>
  );
}
