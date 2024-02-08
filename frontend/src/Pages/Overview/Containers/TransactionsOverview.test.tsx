import { render } from "@testing-library/react"
import { ReactElement } from "react"
import { ErrorBoundary } from "react-error-boundary"
import { QueryClient, QueryClientProvider } from "react-query"
import { expect, it } from "vitest"

import { TransactionsOverview } from "./TransactionsOverview"

// Create a new QueryClient instance for each test
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactElement }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

it("renders the title and data when the query is successful", async () => {
  const Wrapper = createWrapper()
  const { ...result } = render(
    <ErrorBoundary FallbackComponent={Error}>
      <Wrapper>
        <TransactionsOverview endpoint="test" title="Test Title" className="test-class" timeRange="month" />
      </Wrapper>
    </ErrorBoundary>,
  )

  await result.findByText("Test Title")
  expect(result.container).toMatchSnapshot()
})
