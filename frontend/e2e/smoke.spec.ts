import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("demo workflow: load sample, review, filter, inspect, export", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Review your code" })).toBeVisible();
  await expect(page.getByText("Demo mode").first()).toBeVisible();

  // Run is disabled until there is code.
  await expect(page.getByRole("button", { name: "Run review" })).toBeDisabled();

  await page.getByLabel("Load a sample").selectOption({ label: "Python: user service" });
  await expect(page.getByLabel("Code to review")).toHaveValue(/SELECT \* FROM users/);

  await page.getByRole("button", { name: "Run review" }).click();
  await expect(page.getByRole("heading", { name: /Review results/ })).toBeVisible();
  await expect(page.getByText("Demo results.")).toBeVisible();

  // Real numbers from the API: the sample has critical findings and the list matches the summary.
  const total = Number(await page.locator("section[aria-label='Summary'] >> text=Total findings >> xpath=following-sibling::div").first().innerText());
  expect(total).toBeGreaterThan(5);
  await expect(page.getByText(`Showing ${total} of ${total} findings`)).toBeVisible();

  // Filter to critical findings only.
  await page.getByRole("group", { name: "Filter by severity" }).getByRole("button", { name: /^Critical/ }).click();
  const list = page.getByRole("list", { name: "Findings" });
  const items = list.getByRole("listitem");
  expect(await items.count()).toBeGreaterThan(0);
  for (const text of await items.allInnerTexts()) expect(text).toContain("Critical");

  // Reviewer filter narrows further, and a SQL injection finding is explained.
  await page.getByRole("group", { name: "Filter by reviewer" }).getByRole("button", { name: /^Security/ }).click();
  await list.getByRole("button", { name: /SQL built from string concatenation/ }).click();
  const detail = page.getByRole("article");
  await expect(detail).toContainText("Why it matters");
  await expect(detail).toContainText("parameterized queries");

  // Export JSON and check the downloaded file is a demo-labelled review.
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const file = await (await download).path();
  const report = JSON.parse(await readFile(file, "utf-8"));
  expect(report.is_demo).toBe(true);
  expect(report.findings.length).toBe(total);

  // Back to the editor keeps the code.
  await page.getByRole("button", { name: "Edit code" }).click();
  await expect(page.getByLabel("Code to review")).toHaveValue(/SELECT \* FROM users/);
});

test("clean code shows an honest empty state", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Load a sample").selectOption({ label: "Python: clean module" });
  await page.getByRole("button", { name: "Run review" }).click();
  await expect(page.getByRole("heading", { name: "No findings reported" })).toBeVisible();
  await expect(page.getByText("not a guarantee")).toBeVisible();
});

test("live mode without a key explains what to do; no request is made", async ({ page }) => {
  let reviewCalls = 0;
  page.on("request", (r) => r.url().endsWith("/api/review") && reviewCalls++);
  await page.goto("/");
  await page.getByLabel("Code to review").fill("x = 1\n");
  await page.getByLabel(/Live AI/).check();
  await page.getByRole("button", { name: "Run review" }).click();
  await expect(page.getByRole("alert")).toContainText("Enter your API key");
  expect(reviewCalls).toBe(0);
});

test("server errors are shown to the user", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Code to review").fill("x = 1\n");
  await page.route("**/api/review", (route) =>
    route.fulfill({ status: 429, json: { error: { code: "rate_limited", message: "Too many live reviews. Wait a minute." } } }),
  );
  await page.getByRole("button", { name: "Run review" }).click();
  await expect(page.getByRole("alert")).toContainText("Too many live reviews");
});

test("about page is reachable and documents running locally", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "About & docs" }).click();
  await expect(page.getByRole("heading", { name: "About AI Code Review Assistant" })).toBeVisible();
  await expect(page.getByLabel("Backend setup commands")).toContainText("uvicorn");
});

test("keyboard: ctrl+enter runs the review from the editor", async ({ page }) => {
  await page.goto("/");
  const editor = page.getByLabel("Code to review");
  await editor.fill('password = "hunter2hunter2"\n');
  await editor.press("Control+Enter");
  await expect(page.getByRole("heading", { name: /Review results/ })).toBeVisible();
  await expect(page.getByRole("list", { name: "Findings" })).toContainText("Hardcoded secret");
});
