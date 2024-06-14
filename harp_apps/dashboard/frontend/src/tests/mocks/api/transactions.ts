import { http, HttpResponse, PathParams } from "msw"
import { ItemList } from "Domain/Api/Types"
import { Message, Transaction } from "Models/Transaction"

const mockTransactionsFilters = {
  endpoint: {
    values: [
      { name: "endpoint1", count: 10 },
      { name: "endpoint2", count: 20 },
    ],
    current: [],
  },
  method: {
    values: [{ name: "GET" }, { name: "POST" }, { name: "PUT" }, { name: "DELETE" }, { name: "PATCH" }],
    current: [],
  },
  status: {
    values: [{ name: "2xx" }, { name: "3xx" }, { name: "4xx" }, { name: "5xx" }],
    current: [],
  },
  flag: {
    values: [{ name: "flag1" }, { name: "flag2" }],
    current: [],
  },
}
const mockTransaction1: Transaction = {
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
      summary:
        "GET /lorem/ipsum-dolor/sit/amet?this=is&a=very-long&request=path&that-will=demonstrate&how-the-ui=behave-when&the-full-content-with-is-very-large=which-may-happen-quite-often HTTP/1.1",
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

  tags: { foo: "bar", bar: "baz" },
  extras: {},
}

const mockTransaction2: Transaction = {
  id: "EFGH5678",
  type: "GET",
  endpoint: "endpoint1",
  started_at: "2021-08-20T20:00:00Z",
  finished_at: "2021-08-20T20:01:00Z",
  elapsed: 25,
  messages: [
    {
      id: 1,
      transaction_id: "EFGH5678",
      kind: "request",
      summary: "GET /this/is/short HTTP/1.1",
      headers: "headers1",
      body: "body1",
      created_at: "2021-08-20T20:00:00Z",
    } as Message,
    {
      id: 2,
      transaction_id: "EFGH5678",
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
const mockTransactions: { [key: string]: Transaction } = {
  ABCD1234: mockTransaction1,
  EFGH5678: mockTransaction2,
}

export default Object.assign(
  http.get("/api/transactions", () => {
    const transactionsList: ItemList<Transaction> = { items: Object.values(mockTransactions) }
    return HttpResponse.json(transactionsList)
  }),
  {
    filters: http.get("/api/transactions/filters", () => {
      return HttpResponse.json(mockTransactionsFilters)
    }),
    id: http.get<PathParams>("/api/transactions/:id", ({ params }) => {
      const id = params.id as string
      const transaction = mockTransactions[id]
      if (transaction) {
        return HttpResponse.json(transaction)
      } else {
        return HttpResponse.json({ error: "Transaction not found" }, { status: 404 })
      }
    }),
  },
)
