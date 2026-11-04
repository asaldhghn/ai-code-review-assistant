import { expect, test, type Page } from "@playwright/test";

// Common phone and tablet viewport sizes (CSS pixels).
const VIEWPORTS = [
  { name: "small Android 360x640", width: 360, height: 640 },
  { name: "iPhone SE 375x667", width: 375, height: 667 },
  { name: "iPhone 14 390x844", width: 390, height: 844 },
  { name: "Pixel 7 412x915", width: 412, height: 915 },
  { name: "iPad mini 768x1024", width: 768, height: 1024 },
];

async function expectNoHorizontalScroll(page: Page, where: string) {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth, `${where}: page is wider than the viewport`).toBeLessThanOrEqual(innerWidth);
}

for (const vp of VIEWPORTS) {
  test(`usable without sideways scrolling at ${vp.name}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, hasTouch: true });
    const page = await context.newPage();

    await page.goto("/");
    await expectNoHorizontalScroll(page, "workspace");
    await expect(page.getByRole("link", { name: "About & docs" })).toBeVisible();
    await expect(page.getByLabel("Code to review")).toBeVisible();

    await page.getByLabel("Load a sample").selectOption({ label: "Python: user service" });
    const run = page.getByRole("button", { name: "Run review" });
    await run.scrollIntoViewIfNeeded();
    await expect(run).toBeVisible();
    const box = await run.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(40); // comfortable touch target
    await run.tap();

    await expect(page.getByRole("heading", { name: /Review results/ })).toBeVisible();
    await expectNoHorizontalScroll(page, "results");
    await page.getByRole("list", { name: "Findings" }).getByRole("button").first().tap();
    await expect(page.getByRole("article")).toBeVisible();
    await expectNoHorizontalScroll(page, "results with detail");

    await page.goto("/#/about");
    await expectNoHorizontalScroll(page, "about");
    await context.close();
  });
}
