import { fireEvent, screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { describe, expect, it } from "vitest"

import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"

import AuditPage from "./AuditPage"

function answerAs(role: string) {
  server.use(http.get("/api/system", () => HttpResponse.json({ version: "v", revision: "r", user: "alice", role })))
}

function recordRequests(pages = 1) {
  const urls: URL[] = []
  server.use(
    http.get("/api/audit", ({ request }) => {
      urls.push(new URL(request.url))
      return HttpResponse.json({ items: [], total: 41 * pages, pages, perPage: 40 })
    }),
  )
  return urls
}

describe("AuditPage", () => {
  it("lists the events newest first as the API sends them, with who did what to what", async () => {
    answerAs("admin")
    renderWithClient(<AuditPage />)

    await screen.findByText("auth.signed_in")
    const rows = screen.getAllByRole("row").slice(1)
    expect(rows[0]).toHaveTextContent("auth.signed_in")
    expect(rows[0]).toHaveTextContent("alice")
    expect(rows[1]).toHaveTextContent("auth.account.role_changed")
    expect(rows[1]).toHaveTextContent("denied")
    expect(rows[1]).toHaveTextContent("bob")
    expect(rows[1]).toHaveTextContent("account alice")
  })

  it("asks again with the filters once they are applied", async () => {
    answerAs("admin")
    const urls = recordRequests()
    renderWithClient(<AuditPage />)
    await waitFor(() => expect(urls).toHaveLength(1))

    fireEvent.change(screen.getByLabelText("Actor"), { target: { value: "bob" } })
    fireEvent.change(screen.getByLabelText("Action"), { target: { value: "auth." } })
    fireEvent.change(screen.getByLabelText("Target type"), { target: { value: "account" } })
    fireEvent.change(screen.getByLabelText("Target id"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-10-01" } })
    fireEvent.change(screen.getByLabelText("Until"), { target: { value: "2026-10-31" } })
    fireEvent.click(screen.getByRole("button", { name: "Filter" }))

    await waitFor(() => expect(urls).toHaveLength(2))
    expect(Object.fromEntries(urls[1].searchParams)).toEqual({
      page: "1",
      actor: "bob",
      action: "auth.",
      target_type: "account",
      target_id: "1",
      since: "2026-10-01T00:00:00.000Z",
      until: "2026-10-31T23:59:59.999Z",
    })
  })

  it("goes back to the first page when the filters change", async () => {
    answerAs("admin")
    const urls = recordRequests(2)
    renderWithClient(<AuditPage />)
    await waitFor(() => expect(urls).toHaveLength(1))

    fireEvent.click(screen.getAllByRole("link", { name: "Next" })[0])
    await waitFor(() => expect(urls.at(-1)?.searchParams.get("page")).toBe("2"))

    fireEvent.change(screen.getByLabelText("Actor"), { target: { value: "bob" } })
    fireEvent.click(screen.getByRole("button", { name: "Filter" }))
    await waitFor(() => expect(urls.at(-1)?.searchParams.get("actor")).toBe("bob"))
    expect(urls.at(-1)?.searchParams.get("page")).toBe("1")
  })

  it.each(["viewer", "editor"])("tells %s why there is nothing to see, and does not ask for it", async (role) => {
    answerAs(role)
    const urls = recordRequests()
    renderWithClient(<AuditPage />)

    await screen.findByText(/needs the admin role/i)
    expect(urls).toHaveLength(0)
  })
})
