import { CodeXml } from "lucide-react";
import type { ReviewMode } from "../types";
import { ModeBadge } from "./Badges";

export type Page = "workspace" | "about";

interface Props {
  page: Page;
  mode: ReviewMode;
}

const NAV: { id: Page; label: string; href: string }[] = [
  { id: "workspace", label: "Workspace", href: "#/" },
  { id: "about", label: "About & docs", href: "#/about" },
];

export function Header({ page, mode }: Props) {
  return (
    <header className="border-b border-line bg-surface/80 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <a href="#/" className="flex items-center gap-2.5 rounded-md">
          <span className="grid size-8 place-items-center rounded-md border border-line-strong bg-raised text-accent">
            <CodeXml aria-hidden="true" className="size-[18px]" />
          </span>
          <span className="leading-tight">
            <span className="block text-[15px] font-semibold tracking-tight">AI Code Review Assistant</span>
            <span className="hidden text-xs text-muted sm:block">Security &amp; maintainability review</span>
          </span>
        </a>

        <nav aria-label="Main" className="order-3 flex w-full gap-1 sm:order-none sm:w-auto">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={item.href}
              aria-current={page === item.id ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                page === item.id ? "bg-raised text-fg" : "text-muted hover:bg-raised/60 hover:text-fg"
              }`}
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto">
          <ModeBadge mode={mode} />
        </div>
      </div>
    </header>
  );
}
