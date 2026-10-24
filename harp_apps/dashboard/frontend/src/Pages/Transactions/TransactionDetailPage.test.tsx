import { fireEvent } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
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

it("says the response body was truncated when the recording cap cut it", async () => {
  const result = renderDetailAt("/transactions/EFGH5678")

  expect(await result.findByText(/only the beginning of this body was recorded/i)).toHaveAttribute("role", "note")
})

it("says the client left before the end of the response body", async () => {
  const result = renderDetailAt("/transactions/EFGH5678")

  expect(await result.findByText(/the client disconnected before the end of this body/i)).toHaveAttribute(
    "role",
    "note",
  )
})

it("says nothing of truncation or disconnection for a body recorded whole", async () => {
  const result = renderDetailAt("/transactions/ABCD1234")

  await result.findByText("identity")
  expect(result.queryByRole("note")).toBeNull()
})
