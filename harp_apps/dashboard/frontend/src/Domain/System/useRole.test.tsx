import { renderHook, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { describe, expect, it } from "vitest"

import { server } from "tests/mocks/node"
import { createWrapper } from "tests/utils"

import { roleIncludes, useCan, useRole } from "./useRole.ts"

describe("roleIncludes", () => {
  it.each([
    ["viewer", "viewer", true],
    ["viewer", "editor", false],
    ["viewer", "admin", false],
    ["editor", "viewer", true],
    ["editor", "editor", true],
    ["editor", "admin", false],
    ["admin", "viewer", true],
    ["admin", "editor", true],
    ["admin", "admin", true],
  ] as const)("%s includes %s: %s", (role, required, expected) => {
    expect(roleIncludes(role, required)).toBe(expected)
  })

  it("hides nothing while the role is not known, the server enforces it anyway", () => {
    expect(roleIncludes(undefined, "admin")).toBe(true)
  })
})

function answerAs(role: string) {
  server.use(http.get("/api/system", () => HttpResponse.json({ version: "v", revision: "r", user: "alice", role })))
}

describe("useRole", () => {
  it("is the role the request acts with", async () => {
    answerAs("editor")

    const { result } = renderHook(() => useRole(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current).toBe("editor"))
  })

  it("tells whether the role reaches the required one", async () => {
    answerAs("editor")

    const { result } = renderHook(() => [useCan("editor"), useCan("admin")], { wrapper: createWrapper() })

    await waitFor(() => expect(result.current).toEqual([true, false]))
  })
})
