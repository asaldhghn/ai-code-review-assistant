import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, postReview } from "./api";
import { jsonResponse, review } from "./test/fixtures";

const body = { code: "x = 1", language: "python", reviewers: ["security" as const], mode: "live" as const };

afterEach(() => vi.unstubAllGlobals());

describe("postReview", () => {
  it("sends the key only as a header, and only in live mode", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse(review()));
    vi.stubGlobal("fetch", fetchMock);

    await postReview(body, "  sk-test-123  ");
    const live = fetchMock.mock.calls[0]![1] as RequestInit;
    expect((live.headers as Record<string, string>)["X-Api-Key"]).toBe("sk-test-123");
    expect(String(live.body)).not.toContain("sk-test-123");

    await postReview({ ...body, mode: "demo" }, "sk-test-123");
    const demo = fetchMock.mock.calls[1]![1] as RequestInit;
    expect((demo.headers as Record<string, string>)["X-Api-Key"]).toBeUndefined();
  });

  it("turns API error bodies into ApiError with code and message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "rate_limited", message: "Slow down." } }, 429)));
    await expect(postReview(body)).rejects.toMatchObject({ code: "rate_limited", message: "Slow down.", status: 429 });
  });

  it("handles non-JSON error pages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>bad gateway</html>", { status: 502 })));
    await expect(postReview(body)).rejects.toMatchObject({ code: "http_error", status: 502 });
  });

  it("reports network failures with a helpful message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = await postReview(body).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "network_error" });
  });

  it("reports cancellation separately", async () => {
    const controller = new AbortController();
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.reject(new DOMException("aborted", "AbortError"))));
    controller.abort();
    await expect(postReview(body, undefined, controller.signal)).rejects.toMatchObject({ code: "cancelled" });
  });
});
