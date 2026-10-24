import { fireEvent, waitFor } from "@testing-library/react"
import { ErrorBoundary } from "react-error-boundary"
import { afterAll, afterEach, beforeAll, expect, it, vi } from "vitest"

import { Error } from "Components/Page"
import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"
import { Tab } from "ui/Components/Tabs"

import { SystemTopologyTabPanel } from "../SystemTopologyTabPanel"
import RemoteEndpointStatusDropDown from "./RemoteEndpointStatusDropDown"

beforeAll(() => {
  // jsdom has no Web Animations API, which the menu transition of headlessui polls
  Element.prototype.getAnimations = () => []
  vi.stubGlobal("cancelAnimationFrame", (id: number) => window.clearTimeout(id))
})

afterEach(() => {
  server.events.removeAllListeners()
})

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

it("sends each chosen status and replaces the topology with the response", async () => {
  const bodies: unknown[] = []
  server.events.on("request:start", async ({ request }) => {
    if (request.method === "PUT") bodies.push(await request.clone().json())
  })

  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <Tab.Group>
        <SystemTopologyTabPanel />
      </Tab.Group>
    </ErrorBoundary>,
  )

  let current = await result.findByText("up")
  for (const next of ["down", "checking", "up"]) {
    fireEvent.click(current)
    fireEvent.click(await result.findByText(`Set ${next}`))
    current = await result.findByText(next)
  }

  const url = "https://api1.example.com/"
  expect(bodies).toEqual(["down", "checking", "up"].map((action) => ({ endpoint: "endpoint1", url, action })))
})
