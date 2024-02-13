import { renderWithClient } from "tests/utils"
import { expect, it, test } from "vitest"
import { screen } from "@testing-library/react"

import { SystemPage } from "./SystemPage"
import { describe } from "node:test"

describe("SystemPage", () => {
  it("renders the title and data when the query is successful", async () => {
    const result = renderWithClient(<SystemPage />)

    await result.findByText("endpoint1")
    expect(result.container).toMatchSnapshot()
  })

  test("clicking on a tab changes the content", async () => {
    const result = renderWithClient(<SystemPage />)

    await result.findByText("endpoint1")

    const tab = screen.getByText("Settings")
    tab.click()

    await result.findByText("proxy")
    expect(result.findByText("description1")).toBeTruthy()
  })
})
