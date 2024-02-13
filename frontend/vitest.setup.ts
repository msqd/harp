import "@testing-library/jest-dom"
import { server } from "./src/tests/mocks/node"
global.ResizeObserver = require("resize-observer-polyfill");
global.requestAnimationFrame = fn => window.setTimeout(fn, 0);
import { beforeAll, afterEach, afterAll } from 'vitest'

beforeAll(() => {
    server.listen()
  })

afterEach(() => {
    server.resetHandlers()
  })

afterAll(() => {
    server.close()
  })
