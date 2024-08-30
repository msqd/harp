import { http, HttpResponse } from "msw"

const mockProxyData: Apps.Proxy.Endpoint[] = [
  {
    remote: {
      current_pool: ["https://api1.example.com/", "https://api2.example.com/"],
      current_pool_name: "default",
      endpoints: [],
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
export default http.get("/api/system/proxy", () => {
  return HttpResponse.json({
    endpoints: mockProxyData,
  })
})
