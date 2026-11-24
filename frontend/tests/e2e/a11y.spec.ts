import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("M6 Accessibility Audits (WCAG 2.2 AA)", () => {
  test("homepage (/) has zero serious or critical accessibility violations", async ({
    page,
  }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );

    expect(violations).toEqual([]);
  });

  test("about page (/about) has zero serious or critical accessibility violations", async ({
    page,
  }) => {
    await page.goto("/about");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );

    expect(violations).toEqual([]);
  });

  test("404 error page has zero serious or critical accessibility violations", async ({
    page,
  }) => {
    await page.goto("/not-found-page-test");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const violations = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );

    expect(violations).toEqual([]);
  });
});
