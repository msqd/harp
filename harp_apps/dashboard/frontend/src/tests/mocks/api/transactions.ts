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
  cache: {
    values: [{ name: "hit" }, { name: "stale" }, { name: "revalidated" }, { name: "miss" }, { name: "uncacheable" }],
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
  markers: ["client-disconnected", "truncated-response-body"],
}
const mockTransactionNoStore: Transaction = {
  id: "IJKL9012",
  type: "GET",
  endpoint: "endpoint1",
  started_at: "2021-08-20T20:00:00Z",
  finished_at: "2021-08-20T20:01:00Z",
  elapsed: 25,
  messages: [
    {
      id: 1,
      transaction_id: "IJKL9012",
      kind: "request",
      summary: "GET /this/is/short HTTP/1.1",
      created_at: "2021-08-20T20:00:00Z",
    } as Message,
    {
      id: 2,
      transaction_id: "IJKL9012",
      kind: "response",
      summary: "HTTP/1.1 200 OK",
      created_at: "2021-08-20T20:01:00Z",
    } as Message,
  ],
  tags: {},
  extras: {},
  markers: ["no-store-request", "no-store-response"],
}
const mockTransactionOriginNoStore: Transaction = {
  ...mockTransactionNoStore,
  id: "MNOP3456",
  markers: ["no-store-response"],
}
const mockTransactionCacheRevalidated: Transaction = {
  ...mockTransaction1,
  id: "QRST7890",
  tags: {},
  extras: {
    cached: true,
    cache_outcome: "revalidated",
    cache_key: "http://endpoint1/items?" + "a".repeat(64),
    cache_variant: "b".repeat(64),
    cache_seq: 12,
    cache_age: 90,
    cache_ttl: 30,
  },
}
const mockTransactionCacheUncacheable: Transaction = {
  ...mockTransaction1,
  id: "UVWX1234",
  tags: {},
  extras: { cache_outcome: "uncacheable", cache_key: "http://endpoint1/items", cache_seq: 3 },
}
const mockTransactions: { [key: string]: Transaction } = {
  ABCD1234: mockTransaction1,
  EFGH5678: mockTransaction2,
}
// Reachable by id only, so the list (and its snapshot) stays as it was
const mockTransactionsById: { [key: string]: Transaction } = {
  ...mockTransactions,
  IJKL9012: mockTransactionNoStore,
  MNOP3456: mockTransactionOriginNoStore,
  QRST7890: mockTransactionCacheRevalidated,
  UVWX1234: mockTransactionCacheUncacheable,
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
      const transaction = mockTransactionsById[id]
      if (transaction) {
        return HttpResponse.json(transaction)
      } else {
        return HttpResponse.json({ error: "Transaction not found" }, { status: 404 })
      }
    }),
  },
)
