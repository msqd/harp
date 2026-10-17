import { expect, test } from "@playwright/test"
import type { SetupWorker } from "msw/browser"
import type { http, HttpResponse } from "msw"

declare namespace window {
  export const msw: { worker: SetupWorker; http: typeof http; HttpResponse: typeof HttpResponse }
}

test("pause keeps data and manual refresh, resume and navigation restore automatic updates", async ({ page }) => {
  await page.clock.install()
  await page.goto("/")
  await page.getByRole("link", { name: "Transactions", exact: true }).waitFor()
  await page.evaluate(() => {
    const { worker, http, HttpResponse } = window.msw
    let count = 0
    worker.use(
      http.get("/api/transactions", () => {
        document.documentElement.dataset.transactionFetches = String(++count)
        return HttpResponse.json({
          items: [
            {
              id: "PAUSED1234",
              endpoint: "example",
              started_at: "2024-08-15T13:37:42Z",
              elapsed: 60,
              messages: [{ kind: "request", summary: "GET /retained-transaction HTTP/1.1" }],
            },
          ],
          total: 1,
          pages: 1,
          perPage: 20,
        })
      }),
    )
  })
  await page.getByRole("link", { name: "Transactions", exact: true }).click()
  const count = () => page.locator("html").getAttribute("data-transaction-fetches").then(Number)
  await expect(page.getByText("/retained-transaction", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Pause live updates" }).click()
  const pausedCount = await count()
  await page.clock.runFor(30000)
  await page.evaluate(() => window.dispatchEvent(new Event("focus")))
  expect(await count()).toBe(pausedCount)
  await expect(page.getByText("/retained-transaction", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Refresh transactions" }).click()
  await expect.poll(count).toBe(pausedCount + 1)
  await expect(page.getByRole("button", { name: "Resume live updates" })).toBeVisible()

  await page.getByRole("button", { name: "Resume live updates" }).click()
  await page.clock.runFor(10000)
  await expect.poll(count).toBe(pausedCount + 2)
  await page.evaluate(() => window.dispatchEvent(new Event("focus")))
  await expect.poll(count).toBe(pausedCount + 3)

  await page.getByRole("button", { name: "Pause live updates" }).click()
  await page.getByRole("link", { name: "System", exact: true }).click()
  await expect(page).toHaveURL(/\/system$/)
  await expect(page.getByRole("heading", { name: "System", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Resume live updates" })).toHaveCount(0)
  await page.getByRole("link", { name: "Transactions", exact: true }).click()
  await expect(page.getByRole("button", { name: "Pause live updates" })).toBeVisible()
  const returnedCount = await count()
  await page.clock.runFor(10000)
  await expect.poll(count).toBe(returnedCount + 1)
})
