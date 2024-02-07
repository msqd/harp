import "@testing-library/jest-dom"

global.ResizeObserver = require("resize-observer-polyfill");
global.requestAnimationFrame = fn => window.setTimeout(fn, 0);
