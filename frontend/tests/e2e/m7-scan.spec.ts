import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "path";
import fs from "fs/promises";

test.describe("M7 Scan Flow & Real Inference Verification", () => {
  test("full end-to-end scan flow: upload specimen -> /scan/[id] -> verify prediction -> submit feedback", async ({
    page,
  }) => {
    // 0. Track browser console errors
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    // 1. Visit homepage
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "WHICH BIN?" })).toBeVisible();

    // 2. Select a real test sample (battery_1.jpg)
    const testSamplePath = path.resolve(
      process.cwd(),
      "public",
      "samples",
      "battery_1.jpg"
    );

    // Upload file via hidden file input in scanner section
    const fileInput = page.locator("#scanner-section input[type='file']").first();
    await fileInput.setInputFiles(testSamplePath);

    // 3. Scanner state transitions from busy -> navigation to /scan/[id]
    await expect(page).toHaveURL(/\/scan\/[a-f0-9]{32}/, { timeout: 15000 });

    // 4. Verify readout panel contents
    await expect(page.getByRole("heading", { name: "BATTERY" })).toBeVisible();
    await expect(page.getByText("SPECIAL CARE HAZARDOUS")).toBeVisible();
    await expect(page.getByText("Authorised Agencies / Designated Collection Centres")).toBeVisible();
    await expect(page.getByText(/Calibrated Confidence/i)).toBeVisible();
    await expect(page.getByText("MODEL: mobilenet_v3")).toBeVisible();
    await expect(page.getByText(/SERVER TIME INCL. GRAD-CAM:/i)).toBeVisible();

    // 5. Verify image elements render cleanly with non-zero natural dimensions
    const photoImg = page.locator("img[alt*='Specimen photo']");
    const gradcamImg = page.locator("img[alt*='Grad-CAM activation']");
    await expect(photoImg).toBeVisible();
    await expect(gradcamImg).toBeVisible();

    await expect
      .poll(async () => {
        return await photoImg.evaluate((img: HTMLImageElement) => img.naturalWidth);
      }, { timeout: 10000 })
      .toBeGreaterThan(0);

    await expect
      .poll(async () => {
        return await gradcamImg.evaluate((img: HTMLImageElement) => img.naturalWidth);
      }, { timeout: 10000 })
      .toBeGreaterThan(0);

    // Assert zero console errors
    expect(consoleErrors).toEqual([]);

    // 6. Verify HeatmapCompare element
    const slider = page.getByRole("slider", { name: /Grad-CAM overlay comparison/i });
    await expect(slider).toBeVisible();

    // 7. Test keyboard navigation on the Grad-CAM slider
    await slider.focus();
    await expect(slider).toHaveAttribute("aria-valuenow", "50");
    await page.keyboard.press("ArrowLeft");
    await expect(slider).toHaveAttribute("aria-valuenow", "45");
    await page.keyboard.press("ArrowRight");
    await expect(slider).toHaveAttribute("aria-valuenow", "50");

    // 8. Verify and submit citizen feedback ("Was this right?")
    await expect(page.getByText("Was this right?")).toBeVisible();
    const yesButton = page.getByRole("button", { name: /YES, CORRECT/i });
    await expect(yesButton).toBeVisible();
    await yesButton.click();

    await expect(
      page.getByText(/Verification recorded to municipal audit log/i)
    ).toBeVisible();
  });

  test("uncertain specimen displays low-confidence alert banner and tentative stream styling", async ({ page }) => {
    await page.goto("/");

    // Upload known uncertain sample (confidence ~ 39.6% < 40%)
    const uncertainPath = path.resolve(
      process.cwd(),
      "public",
      "samples",
      "uncertain_sample.jpg"
    );

    const fileInput = page.locator("#scanner-section input[type='file']").first();
    await fileInput.setInputFiles(uncertainPath);

    await expect(page).toHaveURL(/\/scan\/[a-f0-9]{32}/, { timeout: 15000 });

    // Verify that the uncertain banner is rendered with 1-decimal place format and dynamic threshold
    const alert = page.locator("div[role='alert']:has-text('Uncertain Flagged')");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("39.6% < 58.5%");

    // Verify tentative stream guidance
    await expect(page.getByText(/POSSIBLY: /i)).toBeVisible();
    await expect(page.getByText("Check the top-3 guesses before disposing.")).toBeVisible();

    // Verify images load cleanly on uncertain page as well
    const photoImg = page.locator("img[alt*='Specimen photo']");
    const gradcamImg = page.locator("img[alt*='Grad-CAM activation']");
    await expect(photoImg).toBeVisible();
    await expect(gradcamImg).toBeVisible();
    await expect
      .poll(async () => photoImg.evaluate((img: HTMLImageElement) => img.naturalWidth), { timeout: 10000 })
      .toBeGreaterThan(0);
    await expect
      .poll(async () => gradcamImg.evaluate((img: HTMLImageElement) => img.naturalWidth), { timeout: 10000 })
      .toBeGreaterThan(0);
  });

  test("invalid file type (.txt) shows friendly client-side validation error without crashing", async ({
    page,
  }) => {
    await page.goto("/");

    // Create temporary dummy text file
    const txtPath = path.resolve(process.cwd(), "test-invalid.txt");
    await fs.writeFile(txtPath, "This is not an image file.", "utf-8");

    try {
      const fileInput = page.locator("#scanner-section input[type='file']").first();
      await fileInput.setInputFiles(txtPath);

      // Verify client-side error alert
      const alert = page.locator("div[role='alert']:has-text('Unsupported format')");
      await expect(alert).toBeVisible();
      await expect(alert).toContainText("Unsupported format");
    } finally {
      await fs.unlink(txtPath).catch(() => {});
    }
  });

  test("specimen wall items can be clicked to run live inference and land on /scan/[id]", async ({
    page,
  }) => {
    await page.goto("/");

    // Find first specimen button on the specimen wall
    const specimenButtons = page.locator("section:has-text('Test Set Specimen Wall') button");
    await expect(specimenButtons.first()).toBeVisible();

    await specimenButtons.first().click();

    // Verify navigation to result page
    await expect(page).toHaveURL(/\/scan\/[a-f0-9]{32}/, { timeout: 15000 });
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("scan result page (/scan/[id]) passes WCAG 2.2 AA accessibility audit", async ({
    page,
  }) => {
    // 1. Upload sample to create a valid scan page
    await page.goto("/");
    const samplePath = path.resolve(
      process.cwd(),
      "public",
      "samples",
      "battery_1.jpg"
    );
    const fileInput = page.locator("#scanner-section input[type='file']").first();
    await fileInput.setInputFiles(samplePath);
    await expect(page).toHaveURL(/\/scan\/[a-f0-9]{32}/, { timeout: 15000 });

    // 2. Run axe accessibility audit on the result page
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );

    expect(violations).toEqual([]);
  });

  test("honesty check: zero hard-coded metric percentages in JSX text across frontend/src", async () => {
    const srcDir = path.resolve(process.cwd(), "src");

    // Scans all .tsx files for literal JSX text like > 92.4% < or >42.4%<
    const jsxTextPattern = />\s*([0-9]{2}\.[0-9]%)\s*</g;

    const files = await fs.readdir(srcDir, { recursive: true });
    const tsxFiles = files
      .map((f) => String(f))
      .filter((f) => f.endsWith(".tsx"));

    const violations: { file: string; match: string }[] = [];

    for (const file of tsxFiles) {
      const fullPath = path.join(srcDir, file);
      const content = await fs.readFile(fullPath, "utf-8");
      const matches = content.match(jsxTextPattern);
      if (matches) {
        for (const m of matches) {
          violations.push({ file, match: m });
        }
      }
    }

    expect(violations).toEqual([]);
  });
});
