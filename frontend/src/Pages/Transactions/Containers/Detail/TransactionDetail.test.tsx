import { expect, it, describe } from "vitest"

import { Transaction, Message } from "Models/Transaction"
import { renderWithClient } from "tests/utils"

import { TransactionDetail } from "./TransactionDetail"

const transaction: Transaction = {
  id: "ABCD1234",
  type: "GET",
  endpoint: "endpoint1",
  started_at: "2021-08-20T20:00:00Z",
  finished_at: "2021-08-20T20:01:00Z",
  elapsed: 60,
  messages: [
    {
      id: 1,
      transaction_id: "ABCD1234",
      kind: "request",
      summary: "GET / HTTP/1.1",
      headers: "headers1",
      body: "body1",
      created_at: "2021-08-20T20:00:00Z",
    } as Message,
    {
      id: 2,
      transaction_id: "ABCD1234",
      kind: "response",
      summary: "HTTP/1.1 200 OK",
      headers: "headers2",
      body: "body2",
      created_at: "2021-08-20T20:01:00Z",
    } as Message,
  ],

  tags: {},
  extras: {},
}

describe("SystemPage", () => {
  it("renders when the query is successful", async () => {
    const result = renderWithClient(<TransactionDetail transaction={transaction} />)

    await result.findByText("identity")
    expect(result.container).toMatchSnapshot()
  })
})
