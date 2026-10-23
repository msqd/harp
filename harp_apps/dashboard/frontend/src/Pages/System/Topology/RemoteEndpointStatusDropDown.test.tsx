import { fireEvent } from "@testing-library/react"
import { ErrorBoundary } from "react-error-boundary"
import { afterEach, beforeAll, expect, it } from "vitest"

import { Error } from "Components/Page"
import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"
import { Tab } from "ui/Components/Tabs"

import { SystemTopologyTabPanel } from "../SystemTopologyTabPanel"

beforeAll(() => {
  // jsdom has no Web Animations API, which the menu transition of headlessui polls
  Element.prototype.getAnimations = () => []
})

afterEach(() => {
  server.events.removeAllListeners()
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
