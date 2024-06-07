import { test, expect, request } from "@playwright/test"

test.beforeEach(async ({ page }) => {
  await page.goto("/transactions")
  await page.waitForFunction(() => document.body.innerText.includes("Endpoint"))
})

test.describe("Transactions Page", () => {
  test("Interacting with the filter side bar", async ({ page }) => {
    const requestMethodButton = await page.$('span:has-text("Request Method")')
    const getLabel = await page.getByLabel("GET")
    expect(getLabel).toBeVisible()
    await requestMethodButton?.click()
    expect(getLabel).not.toBeVisible()

    const endpointButton = await page.getByText("Endpoint", { exact: true })
    const endpoint1Label = await page.getByLabel("endpoint1")
    expect(endpoint1Label).toBeVisible()
    await endpointButton?.click()
    expect(endpoint1Label).not.toBeVisible()

    const responseStatusButton = await page.getByText("Response Status", { exact: true })
    const status200Label = await page.getByLabel("2xx")
    expect(status200Label).toBeVisible()
    await responseStatusButton?.click()
    expect(status200Label).not.toBeVisible()

    await endpointButton?.click()
  })

  test("Clicking filters modify url query params", async ({ page }) => {
    const getQueryParams = () => {
      const PageUrl = new URL(page.url())
      return new URLSearchParams(PageUrl.search)
    }

    let queryParams = getQueryParams()

    // Check for filters
    await page.getByLabel("endpoint2 (20)only").uncheck()
    queryParams = getQueryParams()
    expect(queryParams.get("endpoint")).toBe("endpoint1")
    await page.getByLabel("endpoint2 (20)only").check()
    queryParams = getQueryParams()
    expect(queryParams.get("endpoint")).toBe(null)

    await page.getByLabel("POSTonly").uncheck()
    await page.getByLabel("GETonly").uncheck()
    queryParams = getQueryParams()
    expect(queryParams.getAll("method")).toStrictEqual(["PUT", "DELETE", "PATCH"])

    await page.getByLabel("3xxonly").uncheck()
    queryParams = getQueryParams()
    expect(queryParams.getAll("status")).toStrictEqual(["2xx", "4xx", "5xx"])

    await page.getByLabel("flag1only").uncheck()
    queryParams = getQueryParams()
    expect(queryParams.get("flag")).toBe("flag2")

    await page.getByPlaceholder("Search transactions").dblclick()
    await page.getByPlaceholder("Search transactions").fill("text")
    await page.getByPlaceholder("Search transactions").press("Enter")
    queryParams = getQueryParams()
    expect(queryParams.get("search")).toBe("text")
  })
})
