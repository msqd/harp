import { existsSync, readdirSync, rmSync } from "node:fs"
import { join } from "node:path"

import type { Plugin } from "vite"

/**
 * Empty a directory, sparing the given entries (tracked files that must survive a build).
 */
export function emptyDirExcept(dir: string, keep: string[]) {
  if (!existsSync(dir)) return

  for (const entry of readdirSync(dir)) {
    if (!keep.includes(entry)) rmSync(join(dir, entry), { recursive: true, force: true })
  }
}

/**
 * Replacement for vite's `emptyOutDir`, which would delete the tracked placeholder files too.
 */
export function emptyOutDirExcept(dir: string, keep: string[]): Plugin {
  return {
    name: "harp:empty-out-dir-except",
    apply: "build",
    buildStart() {
      emptyDirExcept(dir, keep)
    },
  }
}
