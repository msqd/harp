import { ErrorBoundary } from "react-error-boundary"
import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"

import { Error } from "Components/Page"

import { TransactionsOverview } from "./TransactionsOverview"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <TransactionsOverview endpoint="test" title="Test Title" className="test-class" timeRange="month" />
    </ErrorBoundary>,
  )

  await result.findByText("Test Title")
  expect(result.container).toMatchSnapshot()
})
