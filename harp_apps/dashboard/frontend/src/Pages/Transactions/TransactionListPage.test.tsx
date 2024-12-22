import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

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
