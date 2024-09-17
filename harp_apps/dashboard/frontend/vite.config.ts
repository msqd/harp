/// <reference types="vitest" />
import { resolve } from "path"

import react from "@vitejs/plugin-react"
import { visualizer } from "rollup-plugin-visualizer"
import tailwindcss from "tailwindcss"
import { defineConfig, loadEnv } from "vite"
import dts from "vite-plugin-dts"
import tsconfigPaths from "vite-tsconfig-paths" // https://vitejs.dev/config/

import pkg from "./package.json" assert { type: "json" }

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const define = {
    "process.env.DISABLE_MOCKS": JSON.stringify(String(!!env.DISABLE_MOCKS)),
    "process.env.NODE_ENV": JSON.stringify(env.NODE_ENV || "production"),
  }
  const build =
    mode === "lib"
      ? {
          lib: {
            entry: [
              resolve(__dirname, "src/index.ts"),
              resolve(__dirname, "src/ui/ui.ts"),
              resolve(__dirname, "src/Domain/hooks.ts"),
              resolve(__dirname, "src/tests/mocks/handlers.ts"),
            ],
            name: "harp-dashboard",
            fileName: (format: string, name: string) => {
              if (format === "es") {
                return `${name}.js`
              }

              return `${name}.${format}`
            },
          },
          rollupOptions: {
            external: [
              ...Object.keys(pkg.dependencies), // don't bundle dependencies
              /^node:.*/, // don't bundle built-in Node.js modules (use protocol imports!)
            ],
          },
          sourcemap: true,
          emptyOutDir: true,
          outDir: "dist",
        }
      : {
          emptyOutDir: true,
          outDir: "../web",
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
              },
            },
          },
        }
  return {
    define,
    build: build,
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
    css: {
      postcss: {
        plugins: [tailwindcss],
      },
    },
    plugins: [
      dts({
        insertTypesEntry: true,
        staticImport: true,
      }),
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
