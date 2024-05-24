import { expect, test } from "@playwright/test"
// we can't create tests asynchronously, thus using the sync-fetch lib
import fetch from "sync-fetch"

// URL where Ladle is served
const url = "http://127.0.0.1:61110"

// set different viewport
// test.use({
//   viewport: { width: 500, height: 400 },
// });

// run tests with browser open
// test.use({ headless: false });

// fetch Ladle's meta file
// https://ladle.dev/docs/meta
const stories = (
  fetch(`${url}/meta.json`).json() as {
    stories: {
      [k: string]: {
        meta?: {
          skip?: boolean
        }
      }
    }
  }
).stories

// iterate through stories
Object.entries(stories).forEach(([name, story]) => {
  // create a test for each story
  test(`${name} - compare snapshots`, async ({ page }) => {
    // skip stories that are marked as skipped
    test.skip(!!story.meta?.skip, "meta.skip is true")
    // navigate to the story
    const previewUrl = `${url}/?story=${name}&mode=preview`
    await page.goto(previewUrl)
    // stories are code-splitted, wait for them
    await page.waitForSelector("[data-storyloaded]")
    // take and compare a screenshot
    await expect(page).toHaveScreenshot(`${name}.png`)
  })
})
