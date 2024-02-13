import { http, HttpResponse, PathParams, RequestHandler } from "msw"

import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery"
import { OverviewData } from "Models/Overview"
import { Transaction, Message } from "Models/Transaction"
import { ItemList } from "Domain/Api/Types"

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
      summary: "GET / HTTP/1.1",
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

const mockOverviewData: OverviewData = {
  errors: {
    count: 10,
    rate: 0.5,
  },
  count: 20,
  meanDuration: 30,
  timeRange: "1h",
  transactions: [
    {
      count: 10,
      datetime: "2021-08-01T00:00:00Z",
      errors: 3,
    },
    {
      count: 20,
      datetime: "2021-08-01T01:00:00Z",
      errors: 5,
    },
  ],
}

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

const mockSettingsData: KeyValueSettings = {
  proxy: {
    endpoints: [
      { name: "endpoint1", port: 8080, url: "http://localhost:8080", description: "description1" },
      { name: "endpoint2", port: 8081, url: "http://localhost:8081", description: "description2" },
    ],
  },
}

interface BlobResponse {
  id: string
  content: string
  contentType: string
}

const mockBlobsResponses: { [key: string]: BlobResponse } = {
  headers1: {
    id: "headers1",
    content: "host: localhost:9001 \n accept-encoding: identity",
    contentType: "__headers__",
  },
  body1: {
    id: "body1",
    content: "body1",
    contentType: "application/json",
  },
  headers2: {
    id: "headers2",
    content: "content-type: application/json",
    contentType: "__headers__",
  },
  body2: {
    id: "body2",
    content: "body2",
    contentType: "application/json",
  },
}
export const handlers: RequestHandler[] = [
  http.get("/api/overview", () => {
    return HttpResponse.json(mockOverviewData)
  }),

  http.get("/api/system/settings", () => {
    return HttpResponse.json(mockSettingsData)
  }),

  http.get("/api/system", () => {
    return HttpResponse.json({ version: "test version", revision: "test revision" })
  }),

  http.get("/api/system/dependencies", () => {
    return HttpResponse.json({ python: ["numpy", "pandas"] })
  }),

  http.get("/api/transactions/filters", () => {
    return HttpResponse.json(mockTransactionsFilters)
  }),

  http.get("/api/blobs/:id", ({ params }) => {
    const id = params.id as string
    const blob = mockBlobsResponses[id]
    if (blob) {
      const buffer = new TextEncoder().encode(blob.content)
      const response = new HttpResponse(buffer, {
        status: 200,
        headers: {
          "Content-Type": blob.contentType,
        },
      })
      return response
    } else {
      return HttpResponse.json({ error: "Blob not found" }, { status: 404 })
    }
  }),

  http.get<PathParams>("/api/transactions/:id", ({ params }) => {
    const id = params.id as string
    const transaction = mockTransactions[id]
    if (transaction) {
      return HttpResponse.json(transaction)
    } else {
      return HttpResponse.json({ error: "Transaction not found" }, { status: 404 })
    }
  }),

  http.get("/api/transactions", () => {
    const transactionsList: ItemList<Transaction> = { items: Object.values(mockTransactions) }
    return HttpResponse.json(transactionsList)
  }),
]
