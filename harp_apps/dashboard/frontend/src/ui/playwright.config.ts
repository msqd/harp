const baseUrl = "http://127.0.0.1:61110"

export default {
  timeout: 10000,
  use: {
    baseURL: baseUrl,
  },
  reporter: [["list"]],
  webServer: {
    command: process.env.TYPE === "dev" ? "pnpm ui:serve" : "pnpm ui:preview",
    env: {
      NODE_ENV: "development",
    },
    url: baseUrl,
    reuseExistingServer: true,
  },
  retries: 0,
  testMatch: "**/tests/**/*.spec.ts",
}
