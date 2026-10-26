import { renderHook, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"

import { server } from "tests/mocks/node"
import { createWrapper } from "tests/utils"

import { useAuditEventsQuery } from "./useAuditEventsQuery"

const page = { items: [], total: 0, pages: 0, perPage: 40 }

function recordRequests() {
  const urls: URL[] = []
  server.use(
    http.get("/api/audit", ({ request }) => {
      urls.push(new URL(request.url))
      return HttpResponse.json(page)
    }),
    http.get("/api/audit/mine", ({ request }) => {
      urls.push(new URL(request.url))
      return HttpResponse.json(page)
    }),
  )
  return urls
}

it("asks the admin API for the page and the filters that are set, leaving the others out", async () => {
  const urls = recordRequests()
  const { result } = renderHook(
    () => useAuditEventsQuery({ page: 2, filters: { actor: "alice", action: "auth.", target_type: "" } }),
    { wrapper: createWrapper() },
  )

  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(urls[0].pathname).toBe("/api/audit")
  expect(Object.fromEntries(urls[0].searchParams)).toEqual({ page: "2", actor: "alice", action: "auth." })
})

it("asks for the activity of the account when mine is set", async () => {
  const urls = recordRequests()
  const { result } = renderHook(() => useAuditEventsQuery({ mine: true }), { wrapper: createWrapper() })

  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(urls[0].pathname).toBe("/api/audit/mine")
})
