import { ErrorBoundary } from "react-error-boundary"
import { it } from "vitest"

import { Error } from "Components/Page"
import { renderWithClient } from "tests/utils.tsx"

import { TransactionsHistory } from "./TransactionsHistory.tsx"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <ErrorBoundary FallbackComponent={Error}>
      <TransactionsHistory endpoint="test" title="Test Title" className="test-class" timeRange="month" />
    </ErrorBoundary>,
  )

  await result.findByText("Test Title")
  // todo see OverViewPage test
  //expect(result.container).toMatchSnapshot()
})
