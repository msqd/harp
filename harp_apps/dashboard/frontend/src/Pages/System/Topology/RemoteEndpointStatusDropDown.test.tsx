import { fireEvent, waitFor } from "@testing-library/react"
import { afterAll, expect, it, vi } from "vitest"

import { renderWithClient } from "tests/utils"

import RemoteEndpointStatusDropDown from "./RemoteEndpointStatusDropDown"

// JSDOM does not implement the Web Animations API used by Headless UI transitions.
Element.prototype.getAnimations = () => []
vi.stubGlobal("cancelAnimationFrame", (id: number) => window.clearTimeout(id))
afterAll(() => vi.unstubAllGlobals())

it("renders the status menu outside the clipping remote table", async () => {
  const result = renderWithClient(
    <div data-testid="remote-table" style={{ overflow: "hidden" }}>
      <RemoteEndpointStatusDropDown
        endpointName="example"
        remoteEndpoint={{ settings: { url: "https://example.com/" }, status: 1 }}
      />
    </div>,
  )

  fireEvent.click(result.getByRole("button", { name: "up" }))

  const menu = await result.findByRole("menu")
  expect(result.getByRole("menuitem", { name: "Set checking" })).toBeVisible()
  expect(result.getByRole("menuitem", { name: "Set down" })).toBeVisible()
  await waitFor(() => expect(result.getByTestId("remote-table")).not.toContainElement(menu), { timeout: 1000 })
  fireEvent.keyDown(menu, { key: "Escape" })
  await waitFor(() => expect(result.queryByRole("menu")).toBeNull())
})
