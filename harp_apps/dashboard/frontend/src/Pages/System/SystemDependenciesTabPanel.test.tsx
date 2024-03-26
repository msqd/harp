import { ErrorBoundary } from "react-error-boundary"
import { expect, it } from "vitest"

import { Error } from "Components/Page"
import { renderWithClient } from "tests/utils"
import { Tab } from "ui/Components/Tabs"

import { SystemDependenciesTabPanel } from "./SystemDependenciesTabPanel"
it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <Tab.Group>
        <SystemDependenciesTabPanel />
      </Tab.Group>
    </ErrorBoundary>,
  )

  await result.findByText("numpy")
  expect(result.container).toMatchSnapshot()
})
