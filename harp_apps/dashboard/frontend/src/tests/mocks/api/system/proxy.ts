import { http, HttpResponse } from "msw"

const mockProxyData: Settings.Proxy.Endpoint[] = [
  {
    name: "endpoint1",
    port: 8080,
    description: "description1",
    remote: {
      endpoints: [],
      min_pool_size: 2,
      probe: {
        type: "http",
        method: "GET",
        path: "/api/health",
      },
      current_pool: ["https://api1.example.com/", "https://api2.example.com/"],
      break_on: ["http_500", "network_error"],
    },
  },
]
export default http.get("/api/system/proxy", () => {
  return HttpResponse.json({
    endpoints: mockProxyData,
  })
})
