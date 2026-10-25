import { http, HttpResponse } from "msw"

export const signedIn = {
  id: 2,
  occurredAt: "2026-10-25T12:00:00Z",
  action: "auth.signed_in",
  outcome: "succeeded",
  actor: { id: 1, label: "alice", via: "session", viaId: "211", client: null },
  ip: "10.0.0.1",
  userAgent: "Firefox",
  target: { type: "account", id: "1", label: "alice" },
  details: { method: "password" },
}

export const roleChanged = {
  id: 1,
  occurredAt: "2026-10-24T08:30:00Z",
  action: "auth.account.role_changed",
  outcome: "denied",
  actor: { id: 2, label: "bob", via: "session", viaId: null, client: null },
  ip: null,
  userAgent: null,
  target: { type: "account", id: "1", label: "alice" },
  details: { from: "viewer", to: "admin" },
}

const page = { items: [signedIn, roleChanged], total: 2, pages: 1, perPage: 40 }

export default Object.assign(
  http.get("/api/audit", () => HttpResponse.json(page)),
  { mine: http.get("/api/audit/mine", () => HttpResponse.json(page)) },
)
