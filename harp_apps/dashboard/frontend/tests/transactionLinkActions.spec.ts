import { expect, test } from "@playwright/test"

function contrast(foreground: number[], background: number[]) {
  const luminance = (rgb: number[]) =>
    rgb
      .map((value) => {
        const channel = value / 255
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
      })
      .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0)
  const [light, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
  return (light + 0.05) / (dark + 0.05)
}

test("transaction copy link matches its neighbour, meets AA and keeps clipboard feedback", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          document.documentElement.dataset.copiedText = text
        },
      },
    })
  })
  await page.goto("/transactions?selected=ABCD1234")
  const text = page.getByText("copy transaction link", { exact: true })
  await expect(text).toBeVisible()
  const control = text.locator("..")
  const openLink = page.getByRole("link", { name: "open in new window" })
  const styles = await text.evaluate((element) => {
    let parent: Element | null = element
    let background = "rgba(0, 0, 0, 0)"
    while (parent && background === "rgba(0, 0, 0, 0)") {
      background = getComputedStyle(parent).backgroundColor
      parent = parent.parentElement
    }
    return { foreground: getComputedStyle(element).color, background }
  })
  const rgb = (value: string) =>
    value
      .match(/[\d.]+/g)!
      .map(Number)
      .slice(0, 3)
  expect(contrast(rgb(styles.foreground), rgb(styles.background))).toBeGreaterThanOrEqual(4.5)
  await expect(text).toHaveCSS("color", await openLink.evaluate((element) => getComputedStyle(element).color))
  await expect(text).toHaveCSS("font-weight", "500")
  await expect(control.locator("svg")).toHaveCSS("width", "12px")
  await expect(control.locator("svg")).toHaveCSS("height", "12px")
  const icon = await control.locator("svg").innerHTML()
  await text.click()
  await expect(page.locator("html")).toHaveAttribute(
    "data-copied-text",
    `${new URL(page.url()).origin}/transactions/ABCD1234`,
  )
  await expect.poll(() => control.locator("svg").innerHTML()).not.toBe(icon)
  await expect(text).toHaveCSS("color", styles.foreground)
  await expect.poll(() => control.locator("svg").innerHTML()).toBe(icon)
  await expect(page).toHaveScreenshot("transaction-detail-copy-link.png")
})
