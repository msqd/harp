/// <reference types="vitest" />
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// https://vitejs.dev/config/
export default defineConfig({
  optimizeDeps: {
    esbuildOptions: {
      target: "es2020",
    },
  },
  esbuild: {
    // https://github.com/vitejs/vite/issues/8644#issuecomment-1159308803
    jsxInject: `import React from 'react'`,
    logOverride: { "this-is-undefined-in-esm": "silent" },
  },
  plugins: [
    react({
      babel: {
        plugins: [
          "babel-plugin-macros",
          [
            "@emotion/babel-plugin-jsx-pragmatic",
            {
              export: "jsx",
              import: "__cssprop",
              module: "@emotion/react",
            },
          ],
          ["@babel/plugin-transform-react-jsx", { pragma: "__cssprop" }, "twin.macro"],
        ],
      },
    }),
  ],
  server: {
    open: "none",
    host: "127.0.0.1",
  },
  preview: {
    open: "none",
    host: "127.0.0.1",
  },
  test: {
    coverage: {
      provider: "v8",
      reporter: ["html", "json", "text"],
      exclude: ["node_modules", "dist", "build", "tests", ".ladle", "**/Styles", "**/*.{js,ts,cjs}", ".*"],
    },
    environment: "jsdom",
    globals: true,
    setupFiles: ["vitest.setup.ts"],
    exclude: ["node_modules", "dist", ".idea", ".git", ".cache", "build", "tests"],
  },
})
