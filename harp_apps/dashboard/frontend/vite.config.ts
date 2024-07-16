/// <reference types="vitest" />
import react from "@vitejs/plugin-react"
import { visualizer } from "rollup-plugin-visualizer"
import { defineConfig, loadEnv } from "vite"
import tsconfigPaths from "vite-tsconfig-paths" // https://vitejs.dev/config/

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const define = {
    "process.env.DISABLE_MOCKS": JSON.stringify(String(!!env.DISABLE_MOCKS)),
    "process.env.NODE_ENV": JSON.stringify(env.NODE_ENV || "production"),
  }
  return {
    define,
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom", "react-is"],
            reactQuery: ["react-query"],
            reactRouter: ["react-router-dom"],
            syntaxHighlighter: ["prismjs", "react-syntax-highlighter"],
            ui: ["@headlessui/react", "@heroicons/react", "@emotion/react"],
            sentry: ["@sentry/browser"],
            dateFns: ["date-fns"],
            echarts: ["echarts"],
            three: ["three"],
          },
        },
      },
    },
    resolve: {
      dedupe: ["@headlessui/react"],
    },
    optimizeDeps: {
      esbuildOptions: {
        target: "es2020",
      },
    },
    esbuild: {
      // https://github.com/vitejs/vite/issues/8644#issuecomment-1159308803
      logOverride: { "this-is-undefined-in-esm": "silent" },
      jsxInject: `import React from 'react'`,
    },
    plugins: [
      tsconfigPaths(),
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
      visualizer(),
    ],
    server: { port: 4999, host: "127.0.0.1" },
    preview: {
      open: "none",
      host: "127.0.0.1",
    },
    test: {
      coverage: {
        provider: "v8",
        reporter: ["html", "json", "text"],
        exclude: [
          "node_modules",
          "dist",
          "build",
          "src/tests",
          ".ladle",
          "**/Styles",
          "**/*.{js,ts,cjs}",
          "**/Domain",
          "**/*.spec.ts",
        ],
        reportsDirectory: "./src/tests/coverage",
      },
      environment: "jsdom",
      globals: true,
      setupFiles: ["vitest.setup.ts"],
      globalSetup: "./vitest.global-setup.ts",
      exclude: ["node_modules", "dist", ".idea", ".git", ".cache", "build", "tests", "src/ui/tests/snapshot.spec.ts"],
    },
  }
})
