// Takes the dashboard captures used by the README and the docs.
//
// Usage: node capture.mjs <base-url> <output-dir>
//
// Playwright comes from the dashboard frontend, so there is nothing more to install than `make install-frontend`
// and the browsers (`pnpm exec playwright install chromium`).
import { createRequire } from "node:module"
import path from "node:path"
import { fileURLToPath } from "node:url"

const here = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(path.join(here, "../../harp_apps/dashboard/frontend/"))
const { chromium } = require("@playwright/test")

const [baseURL, outDir] = process.argv.slice(2)

// Same instant as docs/_captures/seed.py NOW, the clock the seeded data is relative to.
const NOW = new Date("2026-03-12T14:30:00Z")
const VIEWPORT = { width: 1280, height: 800 }
const DETAILS_TRANSACTION_ID = "2gKXOnPpDLBrw0yJDGJ4g5r3qI1"

const shots = [
  { name: "overview", path: "/", ready: "text=Overview" },
  { name: "transactions", path: "/transactions", ready: "table" },
  { name: "transactions-details", path: `/transactions/${DETAILS_TRANSACTION_ID}`, ready: "text=Transaction" },
  { name: "system-settings", path: "/system", tab: "Settings" },
  { name: "system-storage", path: "/system", tab: "Storage" },
  { name: "system-dependencies", path: "/system", tab: "Dependencies" },
]

const browser = await chromium.launch({ args: ["--disable-gpu", "--force-color-profile=srgb", "--font-render-hinting=none"] })
const context = await browser.newContext({
  baseURL,
  viewport: VIEWPORT,
  colorScheme: "light",
  locale: "en-US",
  timezoneId: "UTC",
  reducedMotion: "reduce",
  deviceScaleFactor: 1,
})
await context.addInitScript(() => {
  // No animation, no caret: a capture must not depend on when it is taken.
  const style = document.createElement("style")
  style.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}"
  document.addEventListener("DOMContentLoaded", () => document.head.appendChild(style))
})

for (const shot of shots) {
  const page = await context.newPage()
  await page.clock.install({ time: NOW })
  await page.goto(shot.path)
  if (shot.tab) await page.getByRole("tab", { name: shot.tab }).click()
  if (shot.ready) await page.waitForSelector(shot.ready)
  await page.waitForLoadState("networkidle")
  await page.screenshot({ path: path.join(outDir, `${shot.name}.png`) })
  await page.close()
}

await browser.close()
