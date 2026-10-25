import { fireEvent, screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { afterEach, describe, expect, it, vi } from "vitest"

import { server } from "tests/mocks/node"
import { renderWithClient } from "tests/utils"

import { RightNav } from "./RightNav.tsx"

function answerWith(via: string) {
  server.use(
    http.get("/api/system", () =>
      HttpResponse.json({ version: "v", revision: "r", user: "alice", role: "editor", via }),
    ),
  )
}

describe("RightNav", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("offers to sign out of a session", async () => {
    answerWith("session")

    renderWithClient(<RightNav />)

    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument()
  })

  it("has nothing to sign out of with another way in", async () => {
    answerWith("basic")

    renderWithClient(<RightNav />)

    await screen.findByText("alice")
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument()
  })

  it("ends the session as JSON then goes to the sign in page", async () => {
    answerWith("session")
    const seen: { method: string; contentType: string | null; body: string }[] = []
    server.use(
      http.post("/api/auth/signout", async ({ request }) => {
        seen.push({
          method: request.method,
          contentType: request.headers.get("content-type"),
          body: await request.text(),
        })
        return HttpResponse.json({ ok: true })
      }),
    )
    const assign = vi.fn()
    vi.stubGlobal("location", { ...window.location, assign })
    renderWithClient(<RightNav />)

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }))

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/signin"))
    expect(seen).toEqual([{ method: "POST", contentType: "application/json", body: "{}" }])
  })
})
