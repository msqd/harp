import { http, HttpResponse } from "msw"
import { MemoryRouter } from "react-router"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"

import TransactionListPage from "./TransactionListPage.tsx"
import { TransactionDataTable } from "./Components/List/TransactionDataTable.tsx"

describe("TransactionListPage", () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: new Date("2024-08-15T13:37:42Z") })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("renders well when the query is successful", async () => {
    const result = renderWithClient(
      <MemoryRouter>
        <TransactionListPage TransactionDataTable={TransactionDataTable} />
      </MemoryRouter>,
    )

    await result.findByText("0.06 seconds")
    expect(result.container).toMatchSnapshot()
  })
})

describe("TransactionListPage selection", () => {
  afterEach(() => server.resetHandlers())

  it("shows the not-found state in the detail panel when the selected transaction was removed", async () => {
    server.use(
      http.get("/api/transactions/:id", () => HttpResponse.json({ error: "Transaction not found" }, { status: 404 })),
    )
    const result = renderWithClient(
      <MemoryRouter initialEntries={["/transactions?selected=ABCD1234"]}>
        <TransactionListPage TransactionDataTable={TransactionDataTable} />
      </MemoryRouter>,
    )

    await result.findByText(/does not exist or has been removed/)
    expect(result.queryByText(/Woopsie/)).toBeNull()
  })
})
