import { CircleAlert, FlaskConical, Info, OctagonAlert, Sparkles, TriangleAlert } from "lucide-react";
import { SEVERITY_LABEL } from "../lib/findings";
import type { ReviewMode, Severity } from "../types";

export const SEVERITY_STYLE: Record<Severity, { text: string; bg: string; border: string; bar: string }> = {
  critical: { text: "text-crit", bg: "bg-crit/10", border: "border-crit/40", bar: "bg-crit" },
  warn: { text: "text-warn", bg: "bg-warn/10", border: "border-warn/40", bar: "bg-warn" },
  info: { text: "text-info", bg: "bg-info/10", border: "border-info/40", bar: "bg-info" },
};

const SEVERITY_ICON = { critical: OctagonAlert, warn: TriangleAlert, info: Info } as const;

export function SeverityIcon({ severity, className = "size-4" }: { severity: Severity; className?: string }) {
  const Icon = SEVERITY_ICON[severity] ?? CircleAlert;
  return <Icon aria-hidden="true" className={`${className} ${SEVERITY_STYLE[severity].text}`} />;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const style = SEVERITY_STYLE[severity];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-xs font-semibold ${style.text} ${style.bg} ${style.border}`}
    >
      <SeverityIcon severity={severity} className="size-3.5" />
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

export function ModeBadge({ mode }: { mode: ReviewMode }) {
  if (mode === "demo") {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-sm border border-accent/40 bg-accent/10 px-2 py-1 text-xs font-semibold text-accent-strong"
        title="Findings come from a deterministic rule-based scanner, not an AI model."
      >
        <FlaskConical aria-hidden="true" className="size-3.5" />
        Demo mode
        <span className="font-normal text-muted">rule-based, no AI</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-sm border border-info/40 bg-info/10 px-2 py-1 text-xs font-semibold text-info">
      <Sparkles aria-hidden="true" className="size-3.5" />
      Live AI
    </span>
  );
}
