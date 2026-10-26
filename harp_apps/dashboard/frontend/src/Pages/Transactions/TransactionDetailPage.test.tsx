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

it("says the request asked for no-store when it suppressed both payloads", async () => {
  const result = renderDetailAt("/transactions/IJKL9012")

  const notes = await result.findAllByText(/not recorded: the request carried Cache-Control: no-store/i)
  expect(notes).toHaveLength(2)
  expect(notes[0]).toHaveAttribute("role", "note")
})

it("says the origin asked for no-store when only the response payload was suppressed", async () => {
  const result = renderDetailAt("/transactions/MNOP3456")

  const note = await result.findByText(/not recorded: the response carried Cache-Control: no-store/i)
  expect(note).toHaveAttribute("role", "note")
  expect(result.queryAllByRole("note")).toHaveLength(1)
  const responseTitle = result.getByText("Response")
  expect(responseTitle.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})

it("shows what the cache did: outcome, age, remaining freshness, and which entry", async () => {
  const result = renderDetailAt("/transactions/QRST7890")

  const outcome = await result.findByLabelText("Cache outcome")
  expect(outcome).toHaveTextContent("revalidated")
  expect(result.getByLabelText("Cache age")).toHaveTextContent("1m 30s")
  expect(result.getByLabelText("Cache freshness left")).toHaveTextContent("30s")
  expect(result.getByLabelText("Cache key")).toHaveTextContent("http://endpoint1/items?" + "a".repeat(64))
  expect(result.getByLabelText("Cache variant")).toHaveTextContent("b".repeat(64))
  expect(result.getByLabelText("Cache invalidation number")).toHaveTextContent("12")
})

it("shows an outcome without an entry, age or freshness when the cache kept nothing", async () => {
  const result = renderDetailAt("/transactions/UVWX1234")

  expect(await result.findByLabelText("Cache outcome")).toHaveTextContent("uncacheable")
  expect(result.queryByLabelText("Cache age")).toBeNull()
  expect(result.queryByLabelText("Cache freshness left")).toBeNull()
  expect(result.queryByLabelText("Cache variant")).toBeNull()
})

it("shows no cache section for a transaction the cache did not see", async () => {
  const result = renderDetailAt("/transactions/ABCD1234")

  await result.findByText("identity")
  expect(result.queryByLabelText("Cache outcome")).toBeNull()
})
