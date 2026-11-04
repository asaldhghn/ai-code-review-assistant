import { CircleAlert, X } from "lucide-react";
import type { ApiError } from "../api";

const HINTS: Record<string, string> = {
  missing_credentials: "Add an API key in the settings panel, or switch to Demo mode.",
  invalid_credentials: "Check the key for typos, and that it is active with your AI provider.",
  rate_limited: "Wait a moment before trying again.",
  network_error: "Is the backend running? See the About page for how to start it.",
  live_review_disabled: "Choose Demo mode, or run the project locally with your own key.",
  payload_too_large: "Review a smaller file, or a single function or class.",
  provider_unavailable: "The AI provider may be having trouble. Try again in a minute.",
  invalid_response: "The model returned something unusable. Trying again often works.",
};

export function ErrorBanner({ error, onDismiss }: { error: ApiError; onDismiss?: () => void }) {
  const hint = HINTS[error.code];
  return (
    <div role="alert" className="flex gap-3 rounded-md border border-crit/40 bg-crit/10 p-3 text-sm">
      <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-crit" />
      <div className="min-w-0 flex-1">
        <p className="font-medium text-fg">{error.message}</p>
        {hint && <p className="mt-0.5 text-muted">{hint}</p>}
      </div>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="h-fit rounded-sm p-0.5 text-muted hover:text-fg">
          <X aria-hidden="true" className="size-4" />
        </button>
      )}
    </div>
  );
}
