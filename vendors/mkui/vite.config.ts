import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import istanbul from "vite-plugin-istanbul"

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
    ...(process.env.USE_VITE_PLUGIN_ISTANBUL
      ? [
          istanbul({
            include: "src/*",
            exclude: ["node_modules", "tests/"],
            extension: [".js", ".ts", ".tsx"],
          }),
        ]
      : []),
  ],
  server: {
    open: "none",
    host: "127.0.0.1",
  },
  preview: {
    open: "none",
    host: "127.0.0.1",
  },
})
