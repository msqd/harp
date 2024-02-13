import { test, expect } from "@playwright/test"

test("loads the Overview page", async ({ page }) => {
  await page.goto("/")
  const title = await page.title()
  expect(title).toBe("Harp UI")
})
