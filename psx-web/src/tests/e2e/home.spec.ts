import { expect, test } from "@playwright/test";

test("home page loads and shows app name", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "PSX AI Trading Intelligence"
  );
});
