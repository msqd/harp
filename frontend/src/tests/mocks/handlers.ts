import { http, HttpResponse, RequestHandler } from "msw"

import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery"
import { OverviewData } from "Models/Overview"

const mockData: OverviewData = {
  errors: {
    count: 10,
    rate: 0.5,
  },
  count: 20,
  meanDuration: 30,
  timeRange: "1h",
  transactions: [
    {
      count: 10,
      datetime: "2021-08-01T00:00:00Z",
      errors: 3,
    },
    {
      count: 20,
      datetime: "2021-08-01T01:00:00Z",
      errors: 5,
    },
  ],
}

const mockSettingsData: KeyValueSettings = {
  proxy: {
    endpoints: [
      { name: "endpoint1", port: 8080, url: "http://localhost:8080", description: "description1" },
      { name: "endpoint2", port: 8081, url: "http://localhost:8081", description: "description2" },
    ],
  },
}

export const handlers: RequestHandler[] = [
  http.get("/api/overview", () => {
    return HttpResponse.json(mockData)
  }),

  http.get("/api/system/settings", () => {
    return HttpResponse.json(mockSettingsData)
  }),
]
