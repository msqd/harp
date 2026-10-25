import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"

import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"

import AccountPage from "./AccountPage"

it.each(["viewer", "editor", "admin"])("shows %s the events that concern the account", async (role) => {
  server.use(http.get("/api/system", () => HttpResponse.json({ version: "v", revision: "r", user: "alice", role })))
  let asked = ""
  server.use(
    http.get("/api/audit/mine", ({ request }) => {
      asked = new URL(request.url).pathname
      return HttpResponse.json({
        items: [
          {
            id: 1,
            occurredAt: "2026-10-25T12:00:00Z",
            action: "auth.signed_in",
            outcome: "succeeded",
            actor: { id: 1, label: "alice", via: "session", viaId: null, client: null },
            ip: "10.0.0.1",
            userAgent: "Firefox",
            target: { type: "account", id: "1", label: "alice" },
            details: {},
          },
        ],
        total: 1,
        pages: 1,
        perPage: 40,
      })
    }),
  )
  renderWithClient(<AccountPage />)

  expect(await screen.findByText("auth.signed_in")).toBeTruthy()
  expect(screen.getByText("10.0.0.1")).toBeTruthy()
  expect(asked).toBe("/api/audit/mine")
})

it("says so when nothing happened yet", async () => {
  server.use(http.get("/api/audit/mine", () => HttpResponse.json({ items: [], total: 0, pages: 0, perPage: 40 })))
  renderWithClient(<AccountPage />)

  expect(await screen.findByText(/no activity yet/i)).toBeTruthy()
})
