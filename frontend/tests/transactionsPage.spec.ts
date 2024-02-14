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

    const responseStatusButton = await page.$('span:has-text("Response Status")')
    const status200Label = await page.getByLabel("2xx")
    expect(status200Label).toBeVisible()
    await responseStatusButton?.click()
    expect(status200Label).not.toBeVisible()
  })
})
