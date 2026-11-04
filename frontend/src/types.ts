// Mirrors the FastAPI response models in backend/code_review/schemas.py.

export type Severity = "critical" | "warn" | "info";
export type ReviewerId = "security" | "maintainability";
export type ReviewMode = "demo" | "live";

export interface Finding {
  id: string;
  reviewer: ReviewerId;
  title: string;
  severity: Severity;
  category: string;
  path: string;
  line: number | null;
  description: string;
  why_it_matters: string;
  suggestion: string;
}

export interface ReviewerStatus {
  id: ReviewerId;
  name: string;
  status: "ok" | "failed";
  engine: string;
  finding_count: number;
  error_code: string | null;
  error_message: string | null;
}

export interface ReviewResponse {
  review_id: string;
  mode: ReviewMode;
  is_demo: boolean;
  status: "complete" | "partial";
  created_at: string;
  language: string;
  filename: string;
  line_count: number;
  summary: {
    total: number;
    by_severity: Record<Severity, number>;
    by_reviewer: Record<ReviewerId, number>;
  };
  reviewers: ReviewerStatus[];
  findings: Finding[];
  notices: string[];
}

export interface ReviewRequest {
  code: string;
  language: string;
  filename?: string;
  reviewers: ReviewerId[];
  mode: ReviewMode;
}

export interface AppConfig {
  version: string;
  live_review_enabled: boolean;
  server_key_configured: boolean;
  max_code_chars: number;
  languages: string[];
  reviewers: { id: ReviewerId; name: string }[];
}

export interface SampleSummary {
  id: string;
  title: string;
  language: string;
  filename: string;
  description: string;
}

export interface Sample extends SampleSummary {
  code: string;
}

export type ReportFormat = "html" | "json";
