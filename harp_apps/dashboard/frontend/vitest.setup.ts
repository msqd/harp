// extend Jest's `expect` with matchers that are useful when testing DOM elements.
import "@testing-library/jest-dom"
import "vitest-canvas-mock"
// retrieve our global server mock implementation for auto-registration
import { afterAll, afterEach, beforeAll } from "vitest"

import { server } from "./src/tests/mocks/node"

// polyfill for `ResizeObserver` which is not natively supported in Jest's environment
global.ResizeObserver = require("resize-observer-polyfill")

// mock for `requestAnimationFrame`, which is not available in Node.js where our tests run
global.requestAnimationFrame = (fn) => window.setTimeout(fn, 0)

beforeAll(() => {
  server.listen()
})

afterEach(() => {
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
