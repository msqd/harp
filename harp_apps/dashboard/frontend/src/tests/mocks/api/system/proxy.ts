import { http, HttpResponse } from "msw"

const REMOTE_URL = "https://api1.example.com/"
const STATUS_BY_ACTION: { [action: string]: number } = { up: 1, checking: 0, down: -1 }

const buildMockProxyData = (status: number): Apps.Proxy.Endpoint[] => [
  {
    remote: {
      current_pool: [REMOTE_URL, "https://api2.example.com/"],
      current_pool_name: "default",
      endpoints: [{ settings: { url: REMOTE_URL }, status }],
      probe: {
        settings: {
          method: "GET",
          path: "/api/health",
        },
      },
      settings: {
        min_pool_size: 2,
        break_on: ["http_500", "network_error"],
      },
    },
    settings: {
      name: "endpoint1",
      port: 8080,
      description: "description1",
    },
  },
]
const get = http.get("/api/system/proxy", () => {
  return HttpResponse.json({
    endpoints: buildMockProxyData(STATUS_BY_ACTION.up),
  })
})

const put = http.put("/api/system/proxy", async ({ request }) => {
  const { action } = (await request.json()) as { endpoint: string; url: string; action: string }
  return HttpResponse.json({
    endpoints: buildMockProxyData(STATUS_BY_ACTION[action]),
  })
})

export default Object.assign(get, { put })
