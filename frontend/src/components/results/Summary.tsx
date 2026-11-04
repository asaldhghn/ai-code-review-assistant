import { CircleAlert } from "lucide-react";
import { SEVERITIES, SEVERITY_LABEL, REVIEWER_LABEL } from "../../lib/findings";
import { formatCount } from "../../lib/format";
import type { ReviewResponse, ReviewerId } from "../../types";
import { SEVERITY_STYLE } from "../Badges";

export function Summary({ review }: { review: ReviewResponse }) {
  const { total, by_severity: sev, by_reviewer: rev } = review.summary;
  const distribution = SEVERITIES.map((s) => `${sev[s]} ${SEVERITY_LABEL[s].toLowerCase()}`).join(", ");

  return (
    <section aria-label="Summary" className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Total findings" value={total} />
        {SEVERITIES.map((s) => (
          <Stat key={s} label={SEVERITY_LABEL[s]} value={sev[s]} tone={sev[s] > 0 ? s : undefined} />
        ))}
      </div>

      <div className="grid gap-4 rounded-md border border-line bg-surface p-4 md:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-medium">Severity distribution</h2>
          {total === 0 ? (
            <p className="text-sm text-muted">Nothing to chart: no findings were reported.</p>
          ) : (
            <>
              <div
                role="img"
                aria-label={`Severity distribution: ${distribution}`}
                className="flex h-2.5 overflow-hidden rounded-sm bg-line"
              >
                {SEVERITIES.map((s) =>
                  sev[s] > 0 ? (
                    <div key={s} className={SEVERITY_STYLE[s].bar} style={{ width: `${(sev[s] / total) * 100}%` }} />
                  ) : null,
                )}
              </div>
              <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                {SEVERITIES.map((s) => (
                  <li key={s} className="flex items-center gap-1.5">
                    <span aria-hidden="true" className={`size-2 rounded-full ${SEVERITY_STYLE[s].bar}`} />
                    {SEVERITY_LABEL[s]} {formatCount(sev[s])}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div>
          <h2 className="mb-2 text-sm font-medium">Reviewers</h2>
          <ul className="space-y-1.5 text-sm">
            {review.reviewers.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-x-3">
                <span>
                  {REVIEWER_LABEL[r.id as ReviewerId]}{" "}
                  <span className="text-xs text-muted">· {r.engine}</span>
                </span>
                {r.status === "failed" ? (
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-crit">
                    <CircleAlert aria-hidden="true" className="size-3.5" /> Failed
                  </span>
                ) : (
                  <span className="text-xs text-muted">
                    {formatCount(rev[r.id as ReviewerId])} finding{rev[r.id as ReviewerId] === 1 ? "" : "s"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "critical" | "warn" | "info" }) {
  return (
    <div className="rounded-md border border-line bg-surface px-4 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={`text-2xl font-semibold tabular-nums ${tone ? SEVERITY_STYLE[tone].text : ""}`}>
        {formatCount(value)}
      </div>
    </div>
  );
}
