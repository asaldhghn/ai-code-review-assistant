import { locationOf, REVIEWER_LABEL } from "../../lib/findings";
import { renderInline } from "../../lib/format";
import type { Finding } from "../../types";
import { SeverityBadge } from "../Badges";

interface Props {
  findings: Finding[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function FindingList({ findings, selectedId, onSelect }: Props) {
  return (
    <ul aria-label="Findings" className="space-y-1.5">
      {findings.map((f) => {
        const selected = f.id === selectedId;
        return (
          <li key={f.id}>
            <button
              type="button"
              aria-current={selected ? "true" : undefined}
              onClick={() => onSelect(f.id)}
              className={`w-full rounded-md border p-3 text-left transition-colors ${
                selected ? "border-accent/60 bg-accent/5" : "border-line bg-surface hover:border-line-strong hover:bg-raised"
              }`}
            >
              <span className="mb-1.5 flex items-center gap-2">
                <SeverityBadge severity={f.severity} />
                <span className="text-xs text-muted">{REVIEWER_LABEL[f.reviewer]}</span>
              </span>
              <span className="block text-sm font-medium leading-snug">{renderInline(f.title)}</span>
              <span className="mt-1 block font-mono text-xs text-muted">{locationOf(f)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
