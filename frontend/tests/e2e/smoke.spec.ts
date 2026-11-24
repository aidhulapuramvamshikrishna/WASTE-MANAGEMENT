import { test, expect } from "@playwright/test";
import fs from "fs/promises";
import path from "path";

test.describe("M6 Frontend Foundation Smoke Tests", () => {
  test("homepage loads with industrial header, viewfinder console, streams, and zero CSP errors", async ({
    page,
  }) => {
    const cspErrors: string[] = [];
    page.on("console", (msg) => {
      const text = msg.text();
      if (
        msg.type() === "error" ||
        text.toLowerCase().includes("content security policy") ||
        text.toLowerCase().includes("csp")
      ) {
        if (text.toLowerCase().includes("content security policy")) {
          cspErrors.push(text);
        }
      }
    });

    const response = await page.goto("/");
    expect(response?.status()).toBe(200);

    // 1. Exact title check
    const title = await page.title();
    expect(title).toContain("EcoSort");

    // 2. Visible H1 heading "WHICH BIN?"
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
    await expect(heading).toHaveText("WHICH BIN?");

    // 3. Staged viewfinder console frame is visible with honest telemetry
    await expect(page.getByText("DROP PHOTO · PICK FILE · USE CAMERA")).toBeVisible();
    await expect(page.getByRole("radio", { name: /MobileNetV3/i })).toBeVisible();
    await expect(page.getByText("T = 0.8392 (CALIBRATED)")).toBeVisible();

    // 4. Navigation links are present on desktop
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    await expect(nav.getByRole("link", { name: "Scan" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "History" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Insights" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Model" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "About" })).toBeVisible();

    // 5. Four streams section is present with honest mandates
    await expect(page.getByText("The Four Municipal Streams")).toBeVisible();
    await expect(page.getByText("Mandate: Decentralized Composting / Biomethanation")).toBeVisible();
    await expect(page.getByText("Mandate: Material Recovery Facility (MRF)")).toBeVisible();
    await expect(page.getByText("Mandate: Wrapped securely and stored separately")).toBeVisible();
    await expect(page.getByText("Mandate: Authorised agencies / designated collection centres")).toBeVisible();

    // 6. Zero CSP console errors
    expect(cspErrors).toEqual([]);
  });

  test("/about page loads with report structure, empirical benchmark table, and citations", async ({
    page,
  }) => {
    const response = await page.goto("/about");
    expect(response?.status()).toBe(200);

    const title = await page.title();
    expect(title).toContain("EcoSort");

    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
    await expect(heading).toHaveText("METHODOLOGY & REPORT");

    // Check empirical benchmark table
    await expect(page.getByText("MobileNetV3-Large ★")).toBeVisible();
    await expect(page.getByText("Serving Default")).toBeVisible();

    // Check citations section
    await expect(page.getByText("Solid Waste Management Rules 2026", { exact: true })).toBeVisible();

    // Check that raw LaTeX is not present
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("\\chi");
    expect(bodyText).not.toContain("\\times");
    expect(bodyText).toContain("χ² = 360.36");
  });

  test("/about page dynamically renders exact dataset counts computed from manifest.csv", async ({
    page,
  }) => {
    // 1. Read manifest.csv directly to obtain ground-truth counts
    const manifestPath = path.resolve(
      process.cwd(),
      "..",
      "data",
      "processed",
      "waste12",
      "manifest.csv"
    );
    const content = await fs.readFile(manifestPath, "utf-8");
    const lines = content.split("\n");
    const expectedCounts: Record<string, number> = {
      garbage12: 0,
      realwaste: 0,
      trashbox: 0,
      trashnet: 0,
    };
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const parts = line.split(",");
      if (parts.length >= 5) {
        const src = parts[4].toLowerCase().trim();
        if (expectedCounts[src] !== undefined) {
          expectedCounts[src]++;
        }
      }
    }

    // Ground truth assertions on manifest
    expect(expectedCounts.garbage12).toBe(4605);
    expect(expectedCounts.realwaste).toBe(4752);
    expect(expectedCounts.trashbox).toBe(7072);
    expect(expectedCounts.trashnet).toBe(2522);

    // 2. Navigate to /about and assert rendered counts match manifest counts exactly
    await page.goto("/about");

    const g12El = page.locator('[data-testid="manifest-count-garbage12"]');
    await expect(g12El).toHaveText(`${expectedCounts.garbage12.toLocaleString()} images`);

    const rwEl = page.locator('[data-testid="manifest-count-realwaste"]');
    await expect(rwEl).toHaveText(`${expectedCounts.realwaste.toLocaleString()} images`);

    const tbEl = page.locator('[data-testid="manifest-count-trashbox"]');
    await expect(tbEl).toHaveText(`${expectedCounts.trashbox.toLocaleString()} images`);

    const tnEl = page.locator('[data-testid="manifest-count-trashnet"]');
    await expect(tnEl).toHaveText(`${expectedCounts.trashnet.toLocaleString()} images`);
  });

  test("mobile view (<768px) collapses navigation into an accessible menu button with keyboard support", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/");

    const menuButton = page.locator("#mobile-menu-toggle");
    await expect(menuButton).toBeVisible();
    await expect(menuButton).toHaveAttribute("aria-expanded", "false");

    // Open menu
    await menuButton.click();
    await expect(menuButton).toHaveAttribute("aria-expanded", "true");

    const mobileNav = page.locator("#mobile-nav");
    await expect(mobileNav).toBeVisible();
    await expect(mobileNav.getByRole("link", { name: "Scan" })).toBeVisible();
    await expect(mobileNav.getByRole("link", { name: "About" })).toBeVisible();

    // Escape closes menu and restores focus to menu button
    await page.keyboard.press("Escape");
    await expect(menuButton).toHaveAttribute("aria-expanded", "false");
    await expect(mobileNav).not.toBeVisible();
    await expect(menuButton).toBeFocused();
  });

  test("404 route displays error and return CTA", async ({ page }) => {
    const response = await page.goto("/this-route-does-not-exist");
    expect(response?.status()).toBe(404);

    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
    await expect(heading).toHaveText("ROUTE NOT FOUND");

    const returnBtn = page.getByRole("link", { name: "Return to Scanner" });
    await expect(returnBtn).toBeVisible();
  });
});
