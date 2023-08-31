const baseUrl = "http://127.0.0.1:61110"

export default {
  use: {
    baseURL: baseUrl,
  },
  webServer: {
    command: process.env.TYPE === "dev" ? "pnpm serve:dev" : "pnpm build-preview > /dev/null",
    url: baseUrl,
    reuseExistingServer: true,
  },
  retries: 0,
}