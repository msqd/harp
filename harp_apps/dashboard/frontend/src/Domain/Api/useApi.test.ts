import { afterEach, describe, expect, it, vi } from "vitest"

import { useApi } from "./useApi"

function stubFetch() {
  const fetchMock = vi.fn().mockResolvedValue(new Response("{}"))
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

function sentContentType(fetchMock: ReturnType<typeof stubFetch>) {
  return new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers).get("Content-Type")
}

describe("useApi", () => {
  afterEach(() => vi.unstubAllGlobals())

  it.each(["put", "post", "del"] as const)("%s declares a JSON body, even without one", async (verb) => {
    const fetchMock = stubFetch()

    await useApi()[verb]("/transactions/1/flags/favorite")

    expect(sentContentType(fetchMock)).toBe("application/json")
  })

  it("keeps the other headers the caller passes", async () => {
    const fetchMock = stubFetch()

    await useApi().put("/system/proxy", { headers: { "X-Test": "1" }, body: "{}" })

    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(new Headers(init.headers).get("X-Test")).toBe("1")
    expect(init.method).toBe("PUT")
  })

  it("leaves reads alone", async () => {
    const fetchMock = stubFetch()

    await useApi().get("/system")

    expect(sentContentType(fetchMock)).toBeNull()
  })
})
