import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "path";
import fs from "fs";

const SCREENSHOT_DIR = path.resolve(__dirname, "../screenshots");

test.describe("M8 Pages: History, Insights, and Model Diagnostics", () => {
  test.beforeAll(() => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  // =========================================================================
  // 1. History Page Tests
  // =========================================================================
  test("/history loads with contact sheet, stream filters, and specimen cards", async ({ page }) => {
    await page.goto("/history", { waitUntil: "domcontentloaded" });
    await expect(page.locator("#main-content")).toBeVisible();

    // 1. Heading & Eyebrow
    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toHaveText(/Classification History/i);
    await expect(page.getByText("01 — ARCHIVE")).toBeVisible();

    // 2. Stream Filter Segmented Control
    const filterTabs = page.getByRole("tablist", { name: /Filter predictions/i });
    await expect(filterTabs).toBeVisible();
    await expect(page.getByRole("tab", { name: "ALL" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "WET" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "DRY" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "SANITARY" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "SPECIAL CARE" })).toBeVisible();

    // 3. Filter switching
    const wetTab = filterTabs.getByRole("tab", { name: "WET" });
    await wetTab.click();
    await expect(wetTab).toHaveAttribute("aria-selected", "true");

    const allTab = filterTabs.getByRole("tab", { name: "ALL" });
    await allTab.click();
    await expect(allTab).toHaveAttribute("aria-selected", "true");

    // 4. Check if items exist or empty state is clean
    await expect(page.locator("a[href^='/scan/'], :text('No Specimens Recorded')").first()).toBeVisible();
    const firstCard = page.locator("a[href^='/scan/']").first();
    if (await firstCard.isVisible()) {
      await firstCard.click();
      await page.waitForURL(/\/scan\/[a-f0-9]{32}/, { timeout: 10000 });
      expect(page.url()).toMatch(/\/scan\/[a-f0-9]{32}/);
    }
  });

  // =========================================================================
  // 2. Insights Page Tests
  // =========================================================================
  test("/insights loads with dark control room KPI strip, Recharts, and audit table", async ({ page }) => {
    await page.goto("/insights", { waitUntil: "domcontentloaded" });
    await expect(page.locator("#main-content")).toBeVisible();

    // 1. Heading & Eyebrow
    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toHaveText(/Sorting Insights/i);
    await expect(page.getByText("02 — MUNICIPAL TELEMETRY")).toBeVisible();

    // 2. Control Room KPI Strip
    await expect(page.getByText("Total Scans Logged")).toBeVisible();
    await expect(page.getByText("Recovery Stream Share")).toBeVisible();
    await expect(page.getByText("Citizen Feedback", { exact: true })).toBeVisible();
    await expect(page.getByText("Field Correction Rate")).toBeVisible();

    // 3. Check section headers
    await expect(page.getByRole("heading", { name: "Stream Composition" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Daily Ingestion Volume" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Classification Volume by Material" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Field Feedback & Confusion Pairs" })).toBeVisible();

    // 4. Accessible Data Tables Toggle
    const tableToggle = page.getByRole("button", { name: /ACCESSIBLE DATA TABLES/i });
    await expect(tableToggle).toBeVisible();
    await tableToggle.click();
    await expect(page.getByText("HIDE DATA TABLES")).toBeVisible();
    await expect(page.getByRole("table").first()).toBeVisible();

    // 5. Audit CSV Export Button
    const exportBtn = page.getByRole("link", { name: /EXPORT AUDIT CSV/i });
    await expect(exportBtn).toBeVisible();
    expect(await exportBtn.getAttribute("href")).toBe("/api/v1/admin/feedback.csv");
  });

  // =========================================================================
  // 3. Model Diagnostic Page Tests
  // =========================================================================
  test("/model loads with comparison table, confusion matrix, per-class F1, and training curves", async ({ page }) => {
    await page.goto("/model", { waitUntil: "domcontentloaded" });
    await expect(page.locator("#main-content")).toBeVisible();

    // 1. Heading & Eyebrow
    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toHaveText(/Model Diagnostic Telemetry/i);
    await expect(page.getByText("03 — EVALUATION BENCHMARK")).toBeVisible();

    // 2. Benchmark Synthesis Table
    const compHeading = page.getByRole("heading", { name: "Architecture Comparison" });
    await expect(compHeading).toBeVisible();
    const compTable = page.getByRole("table").first();
    await expect(compTable.getByText("MobileNetV3-Large")).toBeVisible();
    await expect(compTable.getByText("EfficientNet-B0")).toBeVisible();
    await expect(compTable.getByText("WasteNet (from scratch)")).toBeVisible();
    await expect(compTable.getByText("DEFAULT")).toBeVisible();

    // 3. Hypothesis testing callout
    await expect(page.getByText("Hypothesis Testing & Significance Analysis")).toBeVisible();
    await expect(page.getByText(/McNemar test yields χ² = 360.36/i)).toBeVisible();

    // 4. Model Telemetry Switcher
    const archTabs = page.getByRole("tablist", { name: /Select model architecture/i });
    await expect(archTabs).toBeVisible();
    const effTab = page.getByRole("tab", { name: "EfficientNet-B0" });
    await effTab.click();
    await expect(effTab).toHaveAttribute("aria-selected", "true");

    const mobTab = page.getByRole("tab", { name: "MobileNetV3-Large" });
    await mobTab.click();
    await expect(mobTab).toHaveAttribute("aria-selected", "true");

    // 5. Confusion Matrix Heatmap
    await expect(page.getByRole("heading", { name: /Confusion Matrix/i })).toBeVisible();
    const rawBtn = page.getByRole("button", { name: "RAW COUNTS (N)" });
    await rawBtn.click();
    await expect(rawBtn).toContainText("RAW COUNTS (N)");

    const normBtn = page.getByRole("button", { name: "ROW-NORMALIZED (%)" });
    await normBtn.click();
    await expect(normBtn).toContainText("ROW-NORMALIZED (%)");

    // 6. Per-Class Granularity & Source Generalization
    await expect(page.getByRole("heading", { name: "Per-Class Performance" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Source Dataset Accuracy" })).toBeVisible();
    await expect(page.getByText("Temperature Scaling & ECE")).toBeVisible();

    // 7. Training Dynamics
    await expect(page.getByRole("heading", { name: /Training & Validation Dynamics/i })).toBeVisible();
    const epochToggle = page.getByRole("button", { name: /ACCESSIBLE EPOCH TABLE/i });
    await expect(epochToggle).toBeVisible();
    await epochToggle.click();
    await expect(page.getByText("HIDE EPOCH TABLE")).toBeVisible();
  });

  // =========================================================================
  // 4. WCAG 2.2 AA Accessibility Audits
  // =========================================================================
  test("accessibility audit on /history, /insights, and /model has zero serious or critical violations", async ({
    page,
  }) => {
    for (const route of ["/history", "/insights", "/model"]) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await expect(page.locator("#main-content")).toBeVisible();

      const axeResults = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();

      const severeViolations = axeResults.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical"
      );

      expect(
        severeViolations,
        `Severe a11y violations on ${route}: ${JSON.stringify(severeViolations, null, 2)}`
      ).toEqual([]);
    }
  });

  // =========================================================================
  // 5. Visual Artifact Screenshots (375, 768, 1440 px in Light & Dark Mode)
  // =========================================================================
  const viewports = [
    { name: "mobile", width: 375, height: 812 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ];

  for (const vp of viewports) {
    test(`capture screenshots for history at ${vp.width}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/history", { waitUntil: "domcontentloaded" });
      await expect(page.locator("#main-content")).toBeVisible();

      // Light Mode
      await page.evaluate(() => {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("ecosort-theme", "light");
      });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `history_${vp.width}_light.png`),
        fullPage: true,
      });

      // Dark Mode
      await page.evaluate(() => {
        document.documentElement.classList.add("dark");
        localStorage.setItem("ecosort-theme", "dark");
      });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `history_${vp.width}_dark.png`),
        fullPage: true,
      });
    });

    test(`capture screenshots for insights at ${vp.width}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/insights", { waitUntil: "domcontentloaded" });
      await expect(page.locator("#main-content")).toBeVisible();

      // Light Mode
      await page.evaluate(() => {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("ecosort-theme", "light");
      });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `insights_${vp.width}_light.png`),
        fullPage: true,
      });

      // Dark Mode
      await page.evaluate(() => {
        document.documentElement.classList.add("dark");
        localStorage.setItem("ecosort-theme", "dark");
      });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `insights_${vp.width}_dark.png`),
        fullPage: true,
      });
    });

    test(`capture screenshots for model at ${vp.width}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/model", { waitUntil: "domcontentloaded" });
      await expect(page.locator("#main-content")).toBeVisible();

      // Light Mode
      await page.evaluate(() => {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("ecosort-theme", "light");
      });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `model_${vp.width}_light.png`),
        fullPage: true,
      });

      // Dark Mode
      await page.evaluate(() => {
        document.documentElement.classList.add("dark");
        localStorage.setItem("ecosort-theme", "dark");
      });
      await page.waitForTimeout(200);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `model_${vp.width}_dark.png`),
        fullPage: true,
      });
    });
  }
});
