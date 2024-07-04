import { ErrorBoundary } from "react-error-boundary"
import { it } from "vitest"

import { Error } from "Components/Page"
import { renderWithClient } from "tests/utils.tsx"

import { TransactionsHistory } from "./TransactionsHistory.tsx"
import { waitForElementToBeRemoved } from "@testing-library/react"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <TransactionsHistory endpoint="test" title="Test Title" className="test-class" timeRange="month" />
    </ErrorBoundary>,
  )

  await waitForElementToBeRemoved(() => result.getAllByText("Loading..."), { timeout: 5000 })

  await result.findByText("Test Title")
  // TODO: echarts if vary ...
  // expect(result.container).toMatchSnapshot()
})
