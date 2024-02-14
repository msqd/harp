import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { TransactionsListPage } from "./TransactionsListPage"

it("renders well when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter>
      <TransactionsListPage />
    </MemoryRouter>,
  )

  await result.findByText("0.06 seconds")
  expect(result.container).toMatchSnapshot()
})
