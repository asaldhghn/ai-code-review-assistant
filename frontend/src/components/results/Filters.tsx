import { REVIEWER_LABEL, SEVERITIES, SEVERITY_LABEL, countBySeverity, type FindingFilters } from "../../lib/findings";
import type { Finding, ReviewerId } from "../../types";

interface Props {
  findings: Finding[];
  filters: FindingFilters;
  onChange: (filters: FindingFilters) => void;
}

const chip =
  "inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition-colors aria-pressed:border-accent/60 aria-pressed:bg-accent/10 aria-pressed:text-accent-strong border-line-strong bg-raised text-muted hover:text-fg";

export function Filters({ findings, filters, onChange }: Props) {
  const counts = countBySeverity(findings, filters.reviewer);
  const reviewerTotals: Record<ReviewerId, number> = {
    security: findings.filter((f) => f.reviewer === "security").length,
    maintainability: findings.filter((f) => f.reviewer === "maintainability").length,
  };

  return (
    <div className="space-y-3">
      <div role="group" aria-label="Filter by severity" className="flex flex-wrap gap-1.5">
        <button type="button" className={chip} aria-pressed={filters.severity === "all"} onClick={() => onChange({ ...filters, severity: "all" })}>
          All severities
        </button>
        {SEVERITIES.map((s) => (
          <button
            key={s}
            type="button"
            className={chip}
            aria-pressed={filters.severity === s}
            onClick={() => onChange({ ...filters, severity: s })}
          >
            {SEVERITY_LABEL[s]}
            <span className="tabular-nums opacity-80">{counts[s]}</span>
          </button>
        ))}
      </div>
      <div role="group" aria-label="Filter by reviewer" className="flex flex-wrap gap-1.5">
        <button type="button" className={chip} aria-pressed={filters.reviewer === "all"} onClick={() => onChange({ ...filters, reviewer: "all" })}>
          All reviewers
        </button>
        {(["security", "maintainability"] as ReviewerId[]).map((r) => (
          <button
            key={r}
            type="button"
            className={chip}
            aria-pressed={filters.reviewer === r}
            onClick={() => onChange({ ...filters, reviewer: r })}
          >
            {REVIEWER_LABEL[r]}
            <span className="tabular-nums opacity-80">{reviewerTotals[r]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
