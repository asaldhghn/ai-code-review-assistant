// Generates the README screenshots from the real running app. Run with: npm run screenshots
import { test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const out = resolve(process.cwd(), "../screenshots");

test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 (npm run screenshots) to regenerate");

test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });

test("capture screenshots", async ({ page }) => {
  mkdirSync(out, { recursive: true });

  await page.goto("/");
  await page.getByLabel("Load a sample").selectOption({ label: "Python: user service" });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${out}/workspace.png` });

  await page.getByRole("button", { name: "Run review" }).click();
  await page.getByRole("heading", { name: /Review results/ }).waitFor();
  await page.getByRole("list", { name: "Findings" }).getByRole("button", { name: /SQL built/ }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${out}/results.png`, fullPage: true });

  await page.goto("/#/about");
  await page.screenshot({ path: `${out}/about.png`, fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Load a sample").selectOption({ label: "JavaScript: comment widget" });
  await page.getByRole("button", { name: "Run review" }).click();
  await page.getByRole("heading", { name: /Review results/ }).waitFor();
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${out}/results-mobile.png`, fullPage: true });
});
