import { ErrorBoundary } from "react-error-boundary"
import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"

import { Error } from "Components/Page"
import { Tab } from "mkui/Components/Tabs"

import { SystemSettingsTabPanel } from "./SystemSettingsTabPanel"
it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <Tab.Group>
        <SystemSettingsTabPanel />
      </Tab.Group>
    </ErrorBoundary>,
  )

  await result.findByText("endpoint1")
  expect(result.container).toMatchSnapshot()
})
