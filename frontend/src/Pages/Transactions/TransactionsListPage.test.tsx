import { MemoryRouter } from "react-router-dom"
import { expect, it } from "vitest"

import { renderWithClient } from "tests/utils"

import { TransactionListPage } from "./TransactionListPage.tsx"

it("renders well when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter>
      <TransactionListPage />
    </MemoryRouter>,
  )

  await result.findByText("0.06 seconds")
  expect(result.container).toMatchSnapshot()
})
