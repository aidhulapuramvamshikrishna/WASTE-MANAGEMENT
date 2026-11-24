import { test, expect, type Page } from "@playwright/test";
import path from "path";
import fs from "fs";

const SCREENSHOT_DIR = path.resolve(__dirname, "../screenshots");

test.describe("M7 Design System Screenshots (375 / 768 / 1440 px, Light + Dark)", () => {
  test.beforeAll(() => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  const viewports = [
    { name: "mobile", width: 375, height: 812 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ];

  async function capturePage(page: Page, routeUrl: string, prefix: string, width: number, height: number) {
    await page.setViewportSize({ width, height });
    await page.goto(routeUrl);
    await expect(page.locator("#main-content")).toBeVisible();

    if (routeUrl.includes("/scan/")) {
      const photo = page.locator("img[alt*='Specimen photo']");
      await expect(photo).toBeVisible();
      await expect
        .poll(async () => photo.evaluate((img: HTMLImageElement) => img.naturalWidth), { timeout: 10000 })
        .toBeGreaterThan(0);
    }

    // 1. Light Mode
    await page.evaluate(() => {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("ecosort-theme", "light");
    });
    await page.waitForTimeout(300);
    const lightPath = path.join(SCREENSHOT_DIR, `${prefix}_${width}_light.png`);
    await page.screenshot({ path: lightPath, fullPage: true });

    // 2. Dark Mode
    await page.evaluate(() => {
      document.documentElement.classList.add("dark");
      localStorage.setItem("ecosort-theme", "dark");
    });
    await page.waitForTimeout(300);
    const darkPath = path.join(SCREENSHOT_DIR, `${prefix}_${width}_dark.png`);
    await page.screenshot({ path: darkPath, fullPage: true });
  }

  // 1. Capture Home across viewports
  for (const vp of viewports) {
    test(`capture home at ${vp.width}px in light and dark mode`, async ({ page }) => {
      await capturePage(page, "/", "home", vp.width, vp.height);
    });
  }

  // 2. Capture About across viewports
  for (const vp of viewports) {
    test(`capture about at ${vp.width}px in light and dark mode`, async ({ page }) => {
      await capturePage(page, "/about", "about", vp.width, vp.height);
    });
  }

  // 3. Capture Scan Result across viewports
  for (const vp of viewports) {
    test(`capture scan result at ${vp.width}px in light and dark mode`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      const samplePath = path.resolve(process.cwd(), "public", "samples", "battery_1.jpg");
      const fileInput = page.locator("#scanner-section input[type='file']").first();
      await fileInput.setInputFiles(samplePath);
      await page.waitForURL(/\/scan\/[a-f0-9]{32}/, { timeout: 15000 });
      const scanUrl = page.url();

      await capturePage(page, scanUrl, "scan", vp.width, vp.height);
    });
  }

  // 4. Capture Uncertain Example at 1440px desktop
  test("capture uncertain scan result at 1440px in light and dark mode", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    const uncertainPath = path.resolve(process.cwd(), "public", "samples", "uncertain_sample.jpg");
    const fileInput = page.locator("#scanner-section input[type='file']").first();
    await fileInput.setInputFiles(uncertainPath);
    await page.waitForURL(/\/scan\/[a-f0-9]{32}/, { timeout: 15000 });
    const uncertainUrl = page.url();

    await capturePage(page, uncertainUrl, "scan_uncertain", 1440, 900);
  });
});
