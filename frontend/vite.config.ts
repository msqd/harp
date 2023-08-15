import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths"; // https://vitejs.dev/config/
import { visualizer } from "rollup-plugin-visualizer";
// https://vitejs.dev/config/
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-is"],
          reactQuery: ["react-query"],
          reactRouter: ["react-router-dom"],
          ui: [
            "@headlessui/react",
            "@heroicons/react",
            "@emotion/react",
            "@emotion/react",
            "mkui",
          ],
          utils: ["localforage", "match-sorter", "sort-by"],
        },
      },
    },
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
          [
            "@babel/plugin-transform-react-jsx",
            { pragma: "__cssprop" },
            "twin.macro",
          ],
        ],
      },
    }),

    visualizer(),
  ],

  server: { port: 4001 },
});
