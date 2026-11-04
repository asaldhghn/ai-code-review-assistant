import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Automated WCAG 2 A/AA checks with axe-core. This catches many (not all) accessibility problems;
// it does not replace manual keyboard and screen-reader testing.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function scan(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const summary = results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(", ")})`);
  expect(summary, summary.join("\n")).toEqual([]);
}

test("workspace has no detectable WCAG A/AA violations", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Load a sample").selectOption({ label: "Python: user service" });
  await scan(page);
});

test("live-mode settings have no violations", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/Live AI/).check();
  await scan(page);
});

test("results screen has no violations", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Load a sample").selectOption({ label: "JavaScript: comment widget" });
  await page.getByRole("button", { name: "Run review" }).click();
  await page.getByRole("heading", { name: /Review results/ }).waitFor();
  await scan(page);
});

test("about page has no violations", async ({ page }) => {
  await page.goto("/#/about");
  await scan(page);
});

test("keyboard-only: tab order reaches the editor and run button", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab"); // skip link
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await page.getByLabel("Code to review").fill("x = 1");
  const run = page.getByRole("button", { name: "Run review" });
  await run.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: /Review results/ })).toBeVisible();
});
