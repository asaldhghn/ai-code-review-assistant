import { useCallback, useRef, useState } from "react";
import { ApiError, getSample, postReview } from "../api";
import { languageFromFilename } from "../lib/findings";
import type { AppConfig, ReviewerId, ReviewMode, ReviewResponse } from "../types";

const FALLBACK_MAX_CHARS = 60_000;

export interface ReviewedResult {
  review: ReviewResponse;
  /** The exact code that was reviewed (the editor may change afterwards). */
  code: string;
}

export function useReviewSession(config: AppConfig | null) {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [filename, setFilename] = useState<string | undefined>();
  const [reviewers, setReviewers] = useState<ReviewerId[]>(["security", "maintainability"]);
  const [chosenMode, setMode] = useState<ReviewMode>("demo");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<ReviewedResult | null>(null);
  const [view, setView] = useState<"edit" | "results">("edit");
  const abortRef = useRef<AbortController | null>(null);

  const maxChars = config?.max_code_chars ?? FALLBACK_MAX_CHARS;

  // A demo-only server can never run live reviews, whatever was chosen earlier.
  const mode: ReviewMode = config && !config.live_review_enabled ? "demo" : chosenMode;

  const run = useCallback(async () => {
    if (loading) return;
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setLoading(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const review = await postReview(
        { code, language, filename, reviewers, mode },
        mode === "live" ? apiKey : undefined,
        controller.signal,
      );
      setResult({ review, code });
      setView("results");
    } catch (err) {
      if (err instanceof ApiError && err.code === "cancelled") return;
      setError(err instanceof ApiError ? err : new ApiError("Something unexpected went wrong.", "unknown"));
    } finally {
      setLoading(false);
      abortRef.current = null;
    }

    function validate(): ApiError | null {
      if (!code.trim()) return new ApiError("There is no code to review. Paste some code or load a sample first.", "empty_code");
      if (code.length > maxChars) {
        return new ApiError(`The code is longer than the ${maxChars.toLocaleString("en-US")} character limit.`, "payload_too_large");
      }
      if (reviewers.length === 0) return new ApiError("Select at least one reviewer.", "no_reviewers");
      if (mode === "live" && !apiKey.trim() && !config?.server_key_configured) {
        return new ApiError("Enter your API key to run a live AI review, or switch to Demo mode.", "missing_credentials");
      }
      return null;
    }
  }, [loading, code, language, filename, reviewers, mode, apiKey, maxChars, config?.server_key_configured]);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  const loadSample = useCallback(async (id: string) => {
    setError(null);
    try {
      const sample = await getSample(id);
      setCode(sample.code);
      setLanguage(sample.language);
      setFilename(sample.filename);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError("Could not load the sample.", "unknown"));
    }
  }, []);

  const loadFile = useCallback(
    async (file: File) => {
      setError(null);
      if (file.size > maxChars * 4) {
        setError(new ApiError(`"${file.name}" is too large to review (limit ${maxChars.toLocaleString("en-US")} characters).`, "payload_too_large"));
        return;
      }
      const text = await file.text();
      if (text.includes("\u0000") || text.includes("�")) {
        setError(new ApiError(`"${file.name}" does not look like a UTF-8 text file, so it cannot be reviewed.`, "binary_input"));
        return;
      }
      setCode(text);
      setFilename(file.name);
      const detected = languageFromFilename(file.name);
      if (detected) setLanguage(detected);
    },
    [maxChars],
  );

  const clear = useCallback(() => {
    setCode("");
    setFilename(undefined);
    setError(null);
  }, []);

  const toggleReviewer = useCallback((id: ReviewerId) => {
    setReviewers((current) => (current.includes(id) ? current.filter((r) => r !== id) : [...current, id]));
  }, []);

  return {
    code, setCode,
    language, setLanguage,
    filename,
    reviewers, toggleReviewer,
    mode, setMode,
    apiKey, setApiKey,
    loading, error, dismissError: () => setError(null),
    result, view, setView,
    maxChars,
    run, cancel, loadSample, loadFile, clear,
  };
}
