import { MemoryRouter, Route, Routes } from "react-router-dom"
import { expect, it } from "vitest"

import { renderWithClient } from "tests/utils"

import { TransactionsDetailPage } from "./TransactionsDetailPage"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter initialEntries={["/transactions/ABCD1234"]}>
      <Routes>
        <Route path="/transactions/:id" element={<TransactionsDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )

  await result.findByText("identity")
  expect(result.container).toMatchSnapshot()
})
