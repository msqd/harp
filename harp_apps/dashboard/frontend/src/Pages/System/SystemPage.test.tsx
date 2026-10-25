import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { act } from "react"
import { describe, expect, it, test } from "vitest"

import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"

import SystemPage from "./SystemPage"

describe("SystemPage", () => {
  it("renders the title and data when the query is successful", async () => {
    const result = renderWithClient(<SystemPage />)
    expect(result.container).toMatchSnapshot()
  })

  test("clicking on a tab changes the content", async () => {
    const result = renderWithClient(<SystemPage />)
    const tab = screen.getByText("Settings")
    act(() => {
      tab.click()
    })

    await result.findByText("proxy")
    expect(result.findByText("description1")).toBeTruthy()
  })
})

// Keep these below the snapshot test: the ids in the snapshot count the components rendered before it.
describe("SystemPage tabs by role", () => {
  function answerAs(role: string) {
    server.use(http.get("/api/system", () => HttpResponse.json({ version: "v", revision: "r", user: "alice", role })))
  }

  const tabs = () => screen.getAllByRole("tab").map((tab) => tab.textContent)

  it("shows every tab to an admin", async () => {
    answerAs("admin")
    renderWithClient(<SystemPage />)

    await waitFor(() => expect(tabs()).toEqual(["Topology", "Settings", "Storage", "Dependencies"]))
  })

  it("keeps topology and storage for an editor, settings and dependencies are the admin's", async () => {
    answerAs("editor")
    renderWithClient(<SystemPage />)

    await waitFor(() => expect(tabs()).toEqual(["Topology", "Storage"]))
  })

  it("tells a viewer why there is nothing to see", async () => {
    answerAs("viewer")
    const result = renderWithClient(<SystemPage />)

    await result.findByText(/need the editor role/i)
    expect(screen.queryAllByRole("tab")).toEqual([])
  })
})
