import { useEffect, useMemo, useRef } from "react";
import type { Finding, Severity } from "../../types";
import { SEVERITY_STYLE } from "../Badges";
import { SEVERITY_LABEL } from "../../lib/findings";

interface Props {
  code: string;
  findings: Finding[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const RANK: Record<Severity, number> = { critical: 0, warn: 1, info: 2 };

/** Read-only code listing. Lines with findings get a marker; the selected finding's line is highlighted. */
export function CodeView({ code, findings, selectedId, onSelect }: Props) {
  const lines = useMemo(() => code.split("\n"), [code]);
  const selectedRef = useRef<HTMLDivElement>(null);

  // The most severe finding per line decides the marker colour.
  const byLine = useMemo(() => {
    const map = new Map<number, Finding[]>();
    for (const f of findings) {
      if (f.line === null) continue;
      map.set(f.line, [...(map.get(f.line) ?? []), f].sort((a, b) => RANK[a.severity] - RANK[b.severity]));
    }
    return map;
  }, [findings]);

  const selected = findings.find((f) => f.id === selectedId);

  useEffect(() => {
    selectedRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [selectedId]);

  return (
    <section aria-label="Reviewed code" className="rounded-md border border-line bg-surface">
      <h2 className="border-b border-line px-4 py-2 text-xs font-semibold tracking-wide text-muted uppercase">
        Reviewed code
      </h2>
      <div className="max-h-[360px] overflow-auto py-2 font-mono text-[13px] leading-5" tabIndex={0} aria-label="Code listing">
        {lines.map((text, index) => {
          const number = index + 1;
          const here = byLine.get(number);
          const top = here?.[0];
          const isSelected = selected?.line === number;
          return (
            <div
              key={number}
              ref={isSelected ? selectedRef : undefined}
              className={`flex ${isSelected ? "bg-accent/10" : ""}`}
              data-line={number}
            >
              <span className="w-10 shrink-0 pr-2 text-right text-faint select-none">{number}</span>
              <span className="w-6 shrink-0 text-center">
                {top && here && (
                  <button
                    type="button"
                    onClick={() => onSelect(top.id)}
                    aria-label={`Line ${number}: ${here.length} finding${here.length === 1 ? "" : "s"}, most severe ${SEVERITY_LABEL[top.severity]}. Show ${top.title}`}
                    title={top.title}
                    className="inline-grid size-5 place-items-center rounded-sm hover:bg-raised"
                  >
                    <span className={`size-2 rounded-full ${SEVERITY_STYLE[top.severity].bar}`} />
                  </button>
                )}
              </span>
              <pre className="min-w-0 flex-1 pr-4 whitespace-pre">{text || " "}</pre>
            </div>
          );
        })}
      </div>
    </section>
  );
}
