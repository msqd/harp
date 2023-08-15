const baseUrl = 'http://127.0.0.1:61110'

export default {
  use: {
    baseURL: baseUrl,
  },
  webServer: {
    command: process.env.TYPE === "dev" ? "pnpm serve:dev" : "pnpm build-preview",
    url: baseUrl,
  },
  retries: 0,
}
