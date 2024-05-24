import { http, HttpResponse, RequestHandler } from "msw"
import * as api from "./api"

interface BlobResponse {
  id: string
  content: string
  contentType: string
}

const mockBlobsResponses: { [key: string]: BlobResponse } = {
  headers1: {
    id: "headers1",
    content:
      "host: localhost:9001 \n accept-encoding: identity \n x-long-header: Foobar 3r51XEnyibdL3kRyAmts5BSfTyjjOrcbwgr3YOnwUMTcVVLzyhdzEKkQAje2XlXUva59GsJu1Z7IotiVYisO9vDjvHSyLt95SU7WEQNzhKhA7IlT2IQ11Onwmz7su9BT ",
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
  api.overview,
  api.summary,
  api.system,
  api.system.dependencies,
  api.system.settings,
  api.system.storage,

  http.get("/api/blobs/:id", ({ params }) => {
    const id = params.id as string
    const blob = mockBlobsResponses[id]
    if (blob) {
      const buffer = new TextEncoder().encode(blob.content)
      return new HttpResponse(buffer, {
        status: 200,
        headers: {
          "Content-Type": blob.contentType,
        },
      })
    } else {
      return HttpResponse.json({ error: "Blob not found" }, { status: 404 })
    }
  }),
  api.transactions,
  api.transactions.filters,
  api.transactions.id,
]
