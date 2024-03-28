const baseUrl = "http://127.0.0.1:61110"

export default {
  use: {
    baseURL: baseUrl,
  },
  reporter: [["list"]],
  webServer: {
    command: process.env.TYPE === "dev" ? "pnpm ui:serve" : "pnpm ui:preview > /dev/null",
    url: baseUrl,
    reuseExistingServer: true,
  },
  retries: 0,
  testMatch: "**/tests/**/*.spec.ts",
}
