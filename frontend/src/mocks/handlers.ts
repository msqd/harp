import { http, HttpResponse, RequestHandler } from "msw"

import { OverviewData } from "Models/Overview"

const mockData: OverviewData = {
  errors: {
    count: 10,
    rate: 0.5,
  },
  count: 20,
  meanDuration: 30,
  timeRange: "1h",
  transactions: [],
}

export const handlers: RequestHandler[] = [
  http.get("/api/overview", () => {
    console.log("mocking overview")
    return HttpResponse.json(mockData)
  }),
]
