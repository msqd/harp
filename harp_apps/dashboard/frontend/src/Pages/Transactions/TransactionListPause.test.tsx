import { fireEvent } from "@testing-library/react"
import { Link, MemoryRouter, Route, Routes } from "react-router"
import { expect, it } from "vitest"

import { renderWithClient } from "tests/utils"

import { TransactionDataTable } from "./Components/List/TransactionDataTable"
import TransactionListPage from "./TransactionListPage"

it("toggles live updates beside manual refresh and resets after leaving the list", async () => {
  const result = renderWithClient(
    <MemoryRouter initialEntries={["/transactions"]}>
      <Link to="/transactions">Transactions</Link>
      <Link to="/elsewhere">Elsewhere</Link>
      <Routes>
        <Route path="/transactions" element={<TransactionListPage TransactionDataTable={TransactionDataTable} />} />
        <Route path="/elsewhere" element={<p>Other page</p>} />
      </Routes>
    </MemoryRouter>,
  )
  await result.findByText("0.06 seconds")
  const pause = result.getByRole("button", { name: "Pause live updates" })
  const refresh = result.getByRole("button", { name: "Refresh transactions" })
  expect(pause.parentElement).toBe(refresh.parentElement)
  fireEvent.click(pause)
  expect(result.getByRole("button", { name: "Resume live updates" })).toHaveAttribute("aria-pressed", "true")
  expect(result.getByText("0.06 seconds")).toBeVisible()
  fireEvent.click(result.getByRole("button", { name: "Resume live updates" }))
  expect(result.getByRole("button", { name: "Pause live updates" })).toHaveAttribute("aria-pressed", "false")
  fireEvent.click(result.getByRole("button", { name: "Pause live updates" }))
  fireEvent.click(result.getByRole("link", { name: "Elsewhere" }))
  await result.findByText("Other page")
  fireEvent.click(result.getByRole("link", { name: "Transactions" }))
  await result.findByText("0.06 seconds")
  expect(result.getByRole("button", { name: "Pause live updates" })).toHaveAttribute("aria-pressed", "false")
})
