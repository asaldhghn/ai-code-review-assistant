import type { Finding, ReviewerId, Severity } from "../types";

export const SEVERITIES: Severity[] = ["critical", "warn", "info"];

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  warn: "Warning",
  info: "Info",
};

export const REVIEWER_LABEL: Record<ReviewerId, string> = {
  security: "Security",
  maintainability: "Maintainability",
};

export interface FindingFilters {
  severity: Severity | "all";
  reviewer: ReviewerId | "all";
}

export const NO_FILTERS: FindingFilters = { severity: "all", reviewer: "all" };

export function filterFindings(findings: Finding[], filters: FindingFilters): Finding[] {
  return findings.filter(
    (f) =>
      (filters.severity === "all" || f.severity === filters.severity) &&
      (filters.reviewer === "all" || f.reviewer === filters.reviewer),
  );
}

export function hasActiveFilters(filters: FindingFilters): boolean {
  return filters.severity !== "all" || filters.reviewer !== "all";
}

export function locationOf(finding: Pick<Finding, "path" | "line">): string {
  return finding.line === null ? finding.path : `${finding.path}:${finding.line}`;
}

/** Count findings per severity, optionally limited to one reviewer (used by the filter chips). */
export function countBySeverity(findings: Finding[], reviewer: ReviewerId | "all"): Record<Severity, number> {
  const counts: Record<Severity, number> = { critical: 0, warn: 0, info: 0 };
  for (const f of findings) {
    if (reviewer === "all" || f.reviewer === reviewer) counts[f.severity] += 1;
  }
  return counts;
}

const EXTENSION_LANGUAGE: Record<string, string> = {
  py: "python",
  js: "javascript",
  jsx: "javascript",
  mjs: "javascript",
  ts: "typescript",
  tsx: "typescript",
  java: "java",
  go: "go",
  cs: "csharp",
  cpp: "cpp",
  cc: "cpp",
  hpp: "cpp",
  c: "c",
  h: "c",
  rb: "ruby",
  php: "php",
  rs: "rust",
  sql: "sql",
  sh: "shell",
  bash: "shell",
};

export function languageFromFilename(name: string): string | null {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return EXTENSION_LANGUAGE[ext] ?? null;
}

export const LANGUAGE_LABEL: Record<string, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  java: "Java",
  go: "Go",
  csharp: "C#",
  cpp: "C++",
  c: "C",
  ruby: "Ruby",
  php: "PHP",
  rust: "Rust",
  sql: "SQL",
  shell: "Shell",
  other: "Other / plain text",
};
