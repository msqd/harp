import { ErrorBoundary } from "react-error-boundary"
import { expect, it } from "vitest"

import { Error } from "Components/Page"
import { renderWithClient } from "tests/utils"
import { Tab } from "ui/Components/Tabs"

import { SystemTopologyTabPanel } from "./SystemTopologyTabPanel"
it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <Tab.Group>
        <SystemTopologyTabPanel />
      </Tab.Group>
    </ErrorBoundary>,
  )

  await result.findByText("endpoint1")
  expect(result.container).toMatchSnapshot()
})
