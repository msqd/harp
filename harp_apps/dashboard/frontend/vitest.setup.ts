// extend Jest's `expect` with matchers that are useful when testing DOM elements.
import "@testing-library/jest-dom"
import "vitest-canvas-mock"
// retrieve our global server mock implementation for auto-registration
import { afterAll, afterEach, beforeAll, vi } from "vitest"
import { cleanup, configure } from "@testing-library/react"

import { server } from "./src/tests/mocks/node"

// Configure testing-library to wait longer for async operations
// This helps with test isolation issues in containerized environments
configure({ asyncUtilTimeout: 10000 })

// polyfill for `ResizeObserver` which is not natively supported in Jest's environment
global.ResizeObserver = require("resize-observer-polyfill")

// mock for `requestAnimationFrame`, which is not available in Node.js where our tests run
global.requestAnimationFrame = (fn) => window.setTimeout(fn, 0)

beforeAll(() => {
  // Start MSW server - warn on unhandled requests for debugging
  server.listen({ onUnhandledRequest: "warn" })
})

afterEach(() => {
  // Clean up DOM
  cleanup()

  // Reset MSW handlers to initial state
  server.resetHandlers()

  // Clear all mocks and timers
  vi.clearAllMocks()
  vi.clearAllTimers()
  vi.restoreAllMocks()
})

afterAll(() => {
  server.close()
})
