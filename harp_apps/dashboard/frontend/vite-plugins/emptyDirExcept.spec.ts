import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

import { afterEach, beforeEach, describe, expect, it } from "vitest"

import { emptyDirExcept } from "./emptyDirExcept"

describe("emptyDirExcept", () => {
  let dir: string

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "harp-web-"))
  })

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true })
  })

  it("removes files and directories from a previous build", () => {
    writeFileSync(join(dir, "index.html"), "")
    mkdirSync(join(dir, "assets"))
    writeFileSync(join(dir, "assets", "old-123.js"), "")

    emptyDirExcept(dir, [".gitkeep"])

    expect(readdirSync(dir)).toEqual([])
  })

  it("keeps the tracked files", () => {
    writeFileSync(join(dir, ".gitkeep"), "")
    writeFileSync(join(dir, "index.html"), "")

    emptyDirExcept(dir, [".gitkeep"])

    expect(readdirSync(dir)).toEqual([".gitkeep"])
  })

  it("ignores a missing directory", () => {
    const missing = join(dir, "nope")

    emptyDirExcept(missing, [".gitkeep"])

    expect(existsSync(missing)).toBe(false)
  })
})
