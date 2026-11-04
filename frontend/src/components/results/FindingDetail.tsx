import { Check, Copy, Lightbulb, ShieldQuestion, Wrench } from "lucide-react";
import { useState } from "react";
import { locationOf, REVIEWER_LABEL } from "../../lib/findings";
import { renderInline } from "../../lib/format";
import type { Finding } from "../../types";
import { SeverityBadge } from "../Badges";

export function FindingDetail({ finding }: { finding: Finding }) {
  const [copied, setCopied] = useState(false);

  async function copySuggestion() {
    try {
      await navigator.clipboard.writeText(finding.suggestion);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false); // clipboard blocked: the text is still selectable on the page
    }
  }

  return (
    <article aria-label={`Finding ${finding.id}: ${finding.title}`} className="rounded-md border border-line bg-surface">
      <header className="border-b border-line p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          <span className="text-xs text-muted">
            {finding.id} · {REVIEWER_LABEL[finding.reviewer]}
            {finding.category !== finding.reviewer ? ` · ${finding.category}` : ""}
          </span>
        </div>
        <h2 className="text-base font-semibold leading-snug">{renderInline(finding.title)}</h2>
        <p className="mt-1 font-mono text-xs text-muted">{locationOf(finding)}</p>
      </header>

      <div className="space-y-4 p-4 text-sm">
        <Section icon={<ShieldQuestion aria-hidden="true" className="size-4 text-muted" />} title="What is wrong">
          {finding.description}
        </Section>
        <Section icon={<Lightbulb aria-hidden="true" className="size-4 text-warn" />} title="Why it matters">
          {finding.why_it_matters}
        </Section>
        <Section
          icon={<Wrench aria-hidden="true" className="size-4 text-accent" />}
          title="Suggested improvement"
          action={
            <button
              type="button"
              onClick={() => void copySuggestion()}
              className="inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-xs text-muted hover:text-accent-strong"
            >
              {copied ? <Check aria-hidden="true" className="size-3.5" /> : <Copy aria-hidden="true" className="size-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
          }
        >
          {finding.suggestion}
        </Section>
      </div>
    </article>
  );
}

function Section({
  icon,
  title,
  action,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  action?: React.ReactNode;
  children: string;
}) {
  return (
    <section>
      <div className="mb-1 flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted uppercase">
          {icon}
          {title}
        </h3>
        {action}
      </div>
      <p className="leading-relaxed whitespace-pre-wrap text-fg/95">{renderInline(children)}</p>
    </section>
  );
}
