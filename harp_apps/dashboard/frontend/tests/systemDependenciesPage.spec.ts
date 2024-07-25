import { expect, test } from "@playwright/test"
import { SetupWorkerApi } from "msw/browser"
import { http, HttpResponse } from "msw"

declare namespace window {
  export const msw: {
    worker: SetupWorkerApi
    http: typeof http
    HttpResponse: typeof HttpResponse
  }
}

test("Override msw worker for system dependencies", async ({ page }) => {
  await page.goto("/")

  await page.waitForFunction(() => document.body.innerText.includes("Overview"))
  await page.evaluate(() => {
    // Inside this function, you can access the window object and modify the worker
    const { worker, http, HttpResponse } = window.msw
    worker.use(
      http.get("/api/system/dependencies", function override() {
        return HttpResponse.json({ python: ["pydantic", "tensorflow"] })
      }),
    )
  })

  await page.click('a:text("System")')

  await page.click('span:text("Dependencies")')

  // Assert that the text "pydantic" is present on the page
  const text = await page.innerText("body")
  expect(text).toContain("pydantic")
})
