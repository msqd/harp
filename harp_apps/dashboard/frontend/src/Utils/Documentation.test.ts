import { describe, expect, it } from "vitest"

import { getDocumentationUrl } from "./Documentation"

describe("getDocumentationUrl", () => {
  it("points at the documentation matching the running major.minor version", () => {
    expect(getDocumentationUrl("0.10.0")).toContain("/en/0.10/user/")
    expect(getDocumentationUrl("0.9.1")).toContain("/en/0.9/user/")
    expect(getDocumentationUrl("1.0.0")).toContain("/en/1.0/user/")
  })

  it("ignores pre-release and build metadata, which docs are not published per-build", () => {
    expect(getDocumentationUrl("0.10.0a2")).toContain("/en/0.10/user/")
    expect(getDocumentationUrl("0.10.0-alpha2-67-g481856f4-dirty")).toContain("/en/0.10/user/")
  })

  it("falls back to the latest documentation when the version cannot be read", () => {
    expect(getDocumentationUrl(undefined)).toContain("/en/latest/user/")
    expect(getDocumentationUrl("")).toContain("/en/latest/user/")
    expect(getDocumentationUrl("test version")).toContain("/en/latest/user/")
  })

  it("keeps the campaign parameters so documentation traffic stays attributable", () => {
    expect(getDocumentationUrl("0.10.0")).toBe(
      "https://docs.harp-proxy.net/en/0.10/user/?utm_source=dashboard&utm_medium=help",
    )
  })
})
