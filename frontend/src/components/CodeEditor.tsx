import { useRef, type KeyboardEvent } from "react";
import { formatCount } from "../lib/format";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  maxChars: number;
  disabled?: boolean;
}

/** A plain <textarea> with a synchronized line-number gutter. Accessible, no heavy editor bundle. */
export function CodeEditor({ value, onChange, onSubmit, maxChars, disabled }: Props) {
  const gutterRef = useRef<HTMLDivElement>(null);
  const lineCount = Math.max(1, value.split("\n").length);
  const tooLong = value.length > maxChars;

  function syncScroll(event: React.UIEvent<HTMLTextAreaElement>) {
    if (gutterRef.current) gutterRef.current.scrollTop = event.currentTarget.scrollTop;
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <div>
      <div className="flex h-[420px] overflow-hidden rounded-md border border-line bg-surface focus-within:border-accent/60 lg:h-[520px]">
        <div
          ref={gutterRef}
          aria-hidden="true"
          className="select-none overflow-hidden border-r border-line bg-bg/40 py-3 pr-2 pl-3 text-right font-mono text-[13px] leading-5 text-faint"
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>
        <textarea
          aria-label="Code to review"
          aria-describedby="editor-hint"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onScroll={syncScroll}
          onKeyDown={onKeyDown}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          wrap="off"
          placeholder="Paste code here, load a sample, or upload a file…"
          className="min-w-0 flex-1 resize-none bg-transparent px-3 py-3 font-mono text-[13px] leading-5 text-fg placeholder:text-faint focus:outline-none"
        />
      </div>
      <div id="editor-hint" className="mt-2 flex flex-wrap justify-between gap-x-4 gap-y-1 text-xs text-muted">
        <span>
          Press <kbd className="rounded-sm border border-line-strong bg-raised px-1 font-mono">Ctrl</kbd>+
          <kbd className="rounded-sm border border-line-strong bg-raised px-1 font-mono">Enter</kbd> to run a review.
          Code is never executed.
        </span>
        <span className={tooLong ? "font-semibold text-crit" : ""} aria-live="polite">
          {formatCount(value.length)} / {formatCount(maxChars)} characters · {formatCount(lineCount)} lines
          {tooLong ? " (too long)" : ""}
        </span>
      </div>
    </div>
  );
}
