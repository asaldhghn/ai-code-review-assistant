import type {
  AppConfig,
  ReportFormat,
  ReviewRequest,
  ReviewResponse,
  Sample,
  SampleSummary,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const REVIEW_TIMEOUT_MS = 150_000;

/** An error with a stable machine-readable code and a message that is safe to show. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function request(path: string, init: RequestInit = {}, timeoutMs = 30_000): Promise<Response> {
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), timeoutMs);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout.signal]) : timeout.signal;
  try {
    const response = await fetch(`${BASE}${path}`, { ...init, signal });
    if (!response.ok) throw await toApiError(response);
    return response;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (init.signal?.aborted) throw new ApiError("The review was cancelled.", "cancelled");
    if (timeout.signal.aborted) {
      throw new ApiError("The server took too long to answer. Try again with a smaller file.", "timeout");
    }
    throw new ApiError(
      "Could not reach the server. Check that the backend is running and your network is up.",
      "network_error",
    );
  } finally {
    clearTimeout(timer);
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { error?: { code?: string; message?: string } };
    if (body.error?.message) {
      return new ApiError(body.error.message, body.error.code ?? "error", response.status);
    }
  } catch {
    // fall through to the generic message
  }
  return new ApiError(`The server returned an unexpected error (HTTP ${response.status}).`, "http_error", response.status);
}

async function json<T>(path: string, init?: RequestInit, timeoutMs?: number): Promise<T> {
  const response = await request(path, init, timeoutMs);
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("The server sent a response that could not be read.", "invalid_response", response.status);
  }
}

export const getConfig = () => json<AppConfig>("/api/config");
export const getSamples = () => json<SampleSummary[]>("/api/samples");
export const getSample = (id: string) => json<Sample>(`/api/samples/${encodeURIComponent(id)}`);

/** The API key travels only in this request's header; it is never stored by the app. */
export function postReview(body: ReviewRequest, apiKey?: string, signal?: AbortSignal): Promise<ReviewResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (body.mode === "live" && apiKey?.trim()) headers["X-Api-Key"] = apiKey.trim();
  return json<ReviewResponse>(
    "/api/review",
    { method: "POST", headers, body: JSON.stringify(body), signal },
    REVIEW_TIMEOUT_MS,
  );
}

export async function fetchReport(review: ReviewResponse, format: ReportFormat): Promise<Blob> {
  const response = await request(`/api/reports/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(review),
  });
  return response.blob();
}
