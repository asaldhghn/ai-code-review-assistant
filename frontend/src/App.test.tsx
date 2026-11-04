import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { config, jsonResponse, review, samples } from "./test/fixtures";

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;

function mockApi(overrides: Record<string, Handler> = {}) {
  const calls: { url: string; init?: RequestInit }[] = [];
  const routes: Record<string, Handler> = {
    "/api/config": () => jsonResponse(config),
    "/api/samples": () => jsonResponse(samples),
    "/api/samples/py": () => jsonResponse({ ...samples[0], code: "api_key = 'abc'\nx = 1\n" }),
    "/api/review": () => jsonResponse(review()),
    ...overrides,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      const handler = routes[url];
      return handler ? handler(url, init) : jsonResponse({ error: { code: "not_found", message: "nope" } }, 404);
    }),
  );
  return calls;
}

async function renderApp() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("option", { name: "Python: sample" }); // config + samples loaded
  return user;
}

beforeEach(() => {
  window.location.hash = "";
});
afterEach(() => vi.unstubAllGlobals());

describe("workspace", () => {
  it("disables Run until there is code and shows the demo indicator", async () => {
    mockApi();
    const user = await renderApp();
    expect(screen.getAllByText("Demo mode").length).toBeGreaterThan(0);
    const run = screen.getByRole("button", { name: /run review/i });
    expect(run).toBeDisabled();
    await user.type(screen.getByLabelText("Code to review"), "x = 1");
    expect(run).toBeEnabled();
  });

  it("shows the character counter and flags code over the limit", async () => {
    mockApi();
    const user = await renderApp();
    await user.click(screen.getByLabelText("Code to review"));
    await user.paste("a".repeat(1001));
    expect(screen.getByText(/too long/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/character limit/);
  });

  it("requires at least one reviewer", async () => {
    mockApi();
    const user = await renderApp();
    await user.type(screen.getByLabelText("Code to review"), "x");
    await user.click(screen.getByRole("checkbox", { name: /Security/ }));
    await user.click(screen.getByRole("checkbox", { name: /Maintainability/ }));
    expect(screen.getByText("Select at least one reviewer.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run review/i })).toBeDisabled();
  });

  it("live mode asks for a key before calling the API", async () => {
    const calls = mockApi();
    const user = await renderApp();
    await user.type(screen.getByLabelText("Code to review"), "x");
    await user.click(screen.getByRole("radio", { name: /Live AI/ }));
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Enter your API key/);
    expect(calls.some((c) => c.url === "/api/review")).toBe(false);
  });

  it("disables Live AI when the server is demo-only", async () => {
    mockApi({ "/api/config": () => jsonResponse({ ...config, live_review_enabled: false }) });
    await renderApp();
    expect(screen.getByRole("radio", { name: /Live AI/ })).toBeDisabled();
    expect(screen.getByText(/Disabled on this public demo/)).toBeInTheDocument();
  });

  it("loads a sample into the editor", async () => {
    mockApi();
    const user = await renderApp();
    await user.selectOptions(screen.getByLabelText("Load a sample"), "py");
    await waitFor(() => expect(screen.getByLabelText("Code to review")).toHaveValue("api_key = 'abc'\nx = 1\n"));
  });
});

describe("review flow", () => {
  async function runReview(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText("Code to review"), "x = 1");
    await user.click(screen.getByRole("button", { name: /run review/i }));
    await screen.findByRole("heading", { name: /Review results/ });
  }

  it("shows loading state, then results labelled as demo, with real counts", async () => {
    let release: (r: Response) => void = () => undefined;
    mockApi({ "/api/review": () => new Promise<Response>((resolve) => (release = resolve)) });
    const user = await renderApp();
    await user.type(screen.getByLabelText("Code to review"), "x = 1");
    await user.click(screen.getByRole("button", { name: /run review/i }));
    expect(screen.getByRole("button", { name: /Reviewing/ })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/rule-based scanner/);
    release(jsonResponse(review()));

    await screen.findByRole("heading", { name: /Review results/ });
    expect(screen.getByText("Demo results.")).toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "Summary" });
    expect(within(summary).getByText("Total findings").nextSibling).toHaveTextContent("3");
    expect(screen.getByText("Showing 3 of 3 findings")).toBeInTheDocument();
  });

  it("filters by severity and reviewer, and offers a way out of an empty filter", async () => {
    mockApi();
    const user = await renderApp();
    await runReview(user);
    const list = () => screen.getByRole("list", { name: "Findings" });

    await user.click(within(screen.getByRole("group", { name: "Filter by severity" })).getByRole("button", { name: /^Critical/ }));
    expect(within(list()).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("Showing 1 of 3 findings")).toBeInTheDocument();

    await user.click(within(screen.getByRole("group", { name: "Filter by reviewer" })).getByRole("button", { name: /^Maintainability/ }));
    expect(screen.getByText("No findings match these filters.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(within(list()).getAllByRole("listitem")).toHaveLength(3);
  });

  it("shows the explanation and suggested fix of the selected finding", async () => {
    mockApi();
    const user = await renderApp();
    await runReview(user);
    await user.click(within(screen.getByRole("list", { name: "Findings" })).getByRole("button", { name: /Vague name/ }));
    const detail = screen.getByRole("article");
    expect(detail).toHaveTextContent("Vague name");
    expect(detail).toHaveTextContent("Why it matters");
    expect(detail).toHaveTextContent("Load it from the environment.");
  });

  it("renders an honest empty state when nothing was found", async () => {
    mockApi({
      "/api/review": () =>
        jsonResponse(review({ findings: [], summary: { total: 0, by_severity: { critical: 0, warn: 0, info: 0 }, by_reviewer: { security: 0, maintainability: 0 } } })),
    });
    const user = await renderApp();
    await runReview(user);
    expect(screen.getByRole("heading", { name: "No findings reported" })).toBeInTheDocument();
    expect(screen.getByText(/not a guarantee/)).toBeInTheDocument();
  });

  it("flags partial results", async () => {
    mockApi({ "/api/review": () => jsonResponse(review({ status: "partial", is_demo: false, mode: "live", notices: ["Maintainability Critic could not complete: rate limited"] })) });
    const user = await renderApp();
    await runReview(user);
    expect(screen.getByText("Partial result.")).toBeInTheDocument();
    expect(screen.getByText(/could not complete/)).toBeInTheDocument();
    expect(screen.queryByText("Demo results.")).not.toBeInTheDocument();
  });

  it("shows API errors and keeps the user's code", async () => {
    mockApi({ "/api/review": () => jsonResponse({ error: { code: "invalid_credentials", message: "The AI provider rejected the API key." } }, 401) });
    const user = await renderApp();
    await user.type(screen.getByLabelText("Code to review"), "x = 1");
    await user.click(screen.getByRole("button", { name: /run review/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("rejected the API key");
    expect(alert).toHaveTextContent(/Check the key/);
    expect(screen.getByLabelText("Code to review")).toHaveValue("x = 1");
  });

  it("exports a report through the API", async () => {
    const calls = mockApi({ "/api/reports/json": () => new Response("{}", { status: 200 }) });
    URL.createObjectURL = vi.fn(() => "blob:x");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const user = await renderApp();
    await runReview(user);
    await user.click(screen.getByRole("button", { name: /Export JSON/ }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/reports/json")).toBe(true));
    expect(JSON.parse(String(calls.find((c) => c.url === "/api/reports/json")!.init!.body)).review_id).toBe("abc123");
  });

  it("returns to the editor with the code intact", async () => {
    mockApi();
    const user = await renderApp();
    await runReview(user);
    await user.click(screen.getByRole("button", { name: /Edit code/ }));
    expect(screen.getByLabelText("Code to review")).toHaveValue("x = 1");
  });
});

describe("navigation", () => {
  it("shows the About page from the hash and marks it as current", async () => {
    mockApi();
    window.location.hash = "#/about";
    render(<App />);
    expect(await screen.findByRole("heading", { name: /About AI Code Review Assistant/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "About & docs" })).toHaveAttribute("aria-current", "page");
  });
});
