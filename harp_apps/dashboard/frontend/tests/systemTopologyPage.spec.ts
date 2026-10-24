import { expect, test } from "@playwright/test"
import type { SetupWorker } from "msw/browser"
import type { http, HttpResponse } from "msw"

declare namespace window {
  export const msw: { worker: SetupWorker; http: typeof http; HttpResponse: typeof HttpResponse }
}

test("every status entry of the last remote is visible and unobscured", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("link", { name: "System", exact: true }).waitFor()
  await page.evaluate(() => {
    const { worker, http, HttpResponse } = window.msw
    worker.use(
      http.get("/api/system/proxy", () =>
        HttpResponse.json({
          endpoints: [
            {
              settings: { name: "example", port: 8080 },
              remote: {
                current_pool: ["https://first.example.com/", "https://last.example.com/"],
                endpoints: [
                  { settings: { url: "https://first.example.com/" }, status: 1 },
                  { settings: { url: "https://last.example.com/" }, status: 1 },
                ],
              },
            },
          ],
        }),
      ),
    )
  })
  await page.getByRole("link", { name: "System", exact: true }).click()
  const lastStatus = page.getByRole("button", { name: "up", exact: true }).last()
  await lastStatus.click()

  for (const name of ["Set checking", "Set down"]) {
    const item = page.getByRole("menuitem", { name })
    await expect(item).toBeVisible()
    await expect(item).toBeInViewport()
    // Visibility alone does not detect clipping by overflow:hidden. A real hit test does.
    await expect
      .poll(() =>
        item.evaluate((element) => {
          const rect = element.getBoundingClientRect()
          return element.contains(document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2))
        }),
      )
      .toBe(true)
  }

  await page.keyboard.press("Escape")
  await expect(page.getByRole("menu")).not.toBeVisible()
  await expect(lastStatus).toBeFocused()
  await lastStatus.click()
  await expect(page.getByRole("menuitem", { name: "Set down" })).toBeVisible()
})
