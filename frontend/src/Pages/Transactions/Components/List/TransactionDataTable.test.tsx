import { render, fireEvent } from "@testing-library/react"
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest"

import { Transaction } from "Models/Transaction"

import { TransactionDataTable } from "./TransactionDataTable"

const transactions: Transaction[] = [
  {
    id: "1",
    type: "GET",
    endpoint: "/api/v1/users",
    started_at: "2022-03-01T12:00:00Z",
    finished_at: "2022-03-01T12:00:02Z",
    elapsed: 2000,
    messages: [],
    tags: {
      module: "users",
    },
    extras: {
      flags: ["favorite"],
    },
  },
  {
    id: "2",
    type: "POST",
    endpoint: "/api/v1/users",
    started_at: "2022-03-01T12:05:00Z",
    finished_at: "2022-03-01T12:05:03Z",
    elapsed: 3000,
    messages: [],
    tags: {
      module: "users",
    },
    extras: {
      flags: [],
    },
  },
  {
    id: "3",
    type: "DELETE",
    endpoint: "/api/v1/users/1",
    started_at: "2022-03-01T12:10:00Z",
    finished_at: "2022-03-01T12:10:01Z",
    elapsed: 1000,
    messages: [],
    tags: {
      module: "users",
    },
    extras: {
      flags: ["favorite"],
    },
  },
]

describe("TransactionDataTable", () => {
  beforeAll(() => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    vi.mock("Domain/Transactions", () => ({
      useSetUserFlagMutation: () => ({ mutate: vi.fn() }),
    }))

    vi.mock("react-router-dom", async () => {
      const navigate = vi.fn()
      const actualReactRouterDom = await vi.importActual("react-router-dom")
      return {
        ...actualReactRouterDom,
        useNavigate: () => navigate,
      }
    })
  })

  afterAll(() => {
    vi.restoreAllMocks()
  })

  it("renders the correct number of rows", () => {
    const { getAllByRole } = render(<TransactionDataTable transactions={transactions} />)

    const rows = getAllByRole("row")
    expect(rows).toHaveLength(transactions.length + 1)
  })

  it("calls navigate when a row is clicked", async () => {
    const reactRouterDom = await import("react-router-dom")
    const navigate = reactRouterDom.useNavigate()

    const { getAllByRole } = render(<TransactionDataTable transactions={transactions} />)

    const rows = getAllByRole("row")
    fireEvent.click(rows[1])

    expect(navigate).toHaveBeenCalledWith("/transactions/1")
  })
})
