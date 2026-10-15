import { fireEvent } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { expect, it, vi } from "vitest"

import { renderWithClient } from "tests/utils"

import TransactionDetailPage from "./TransactionDetailPage.tsx"

function renderDetailAt(path: string) {
  return renderWithClient(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/transactions/:id" element={<TransactionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

it("renders the title and data when the query is successful", async () => {
  const result = renderDetailAt("/transactions/ABCD1234")

  await result.findByText("identity")
  expect(result.container).toMatchSnapshot()
})

it("says the transaction does not exist, with no copy link, when the id is unknown", async () => {
  const result = renderDetailAt("/transactions/UNKNOWN")

  await result.findByText(/does not exist or has been removed/)
  expect(result.queryByText("copy transaction link")).toBeNull()
})

it("copies the transaction link as /transactions/<id> from the detail page", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true })
  const result = renderDetailAt("/transactions/ABCD1234")

  fireEvent.click(await result.findByText("copy transaction link"))
  expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/transactions/ABCD1234`)
})
