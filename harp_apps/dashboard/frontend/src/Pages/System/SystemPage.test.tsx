import { screen } from "@testing-library/react"
import { act } from "react-dom/test-utils"
import { expect, it, test, describe } from "vitest"

import { renderWithClient } from "tests/utils"

import { SystemPage } from "./SystemPage"

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
    act(() => {
      tab.click()
    })

    await result.findByText("proxy")
    expect(result.findByText("description1")).toBeTruthy()
  })
})
