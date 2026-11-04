import type { AppConfig, Finding, ReviewResponse, SampleSummary } from "../types";

export const config: AppConfig = {
  version: "1.0.0",
  live_review_enabled: true,
  server_key_configured: false,
  max_code_chars: 1000,
  languages: ["python", "javascript", "other"],
  reviewers: [
    { id: "security", name: "Security Auditor" },
    { id: "maintainability", name: "Maintainability Critic" },
  ],
};

export const samples: SampleSummary[] = [
  { id: "py", title: "Python: sample", language: "python", filename: "sample.py", description: "demo" },
];

export function finding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: "S1",
    reviewer: "security",
    title: "Hardcoded secret in `api_key`",
    severity: "critical",
    category: "security",
    path: "snippet.py",
    line: 2,
    description: "A credential is in the source.",
    why_it_matters: "Anyone with repo access can use it.",
    suggestion: "Load it from the environment.",
    ...overrides,
  };
}

export function review(overrides: Partial<ReviewResponse> = {}): ReviewResponse {
  const findings = [
    finding(),
    finding({ id: "M1", reviewer: "maintainability", severity: "warn", category: "naming", title: "Vague name", line: 1 }),
    finding({ id: "M2", reviewer: "maintainability", severity: "info", category: "style", title: "Loose style", line: null }),
  ];
  return {
    review_id: "abc123",
    mode: "demo",
    is_demo: true,
    status: "complete",
    created_at: "2026-01-01T12:00:00Z",
    language: "python",
    filename: "snippet.py",
    line_count: 3,
    summary: {
      total: 3,
      by_severity: { critical: 1, warn: 1, info: 1 },
      by_reviewer: { security: 1, maintainability: 2 },
    },
    reviewers: [
      { id: "security", name: "Security Auditor", status: "ok", engine: "demo", finding_count: 1, error_code: null, error_message: null },
      { id: "maintainability", name: "Maintainability Critic", status: "ok", engine: "demo", finding_count: 2, error_code: null, error_message: null },
    ],
    findings,
    notices: ["Demo mode: these findings come from a deterministic rule-based scanner, not from an AI model."],
    ...overrides,
  };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
