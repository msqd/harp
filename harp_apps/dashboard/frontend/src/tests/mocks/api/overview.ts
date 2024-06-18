import { http, HttpResponse } from "msw"
import { OverviewData } from "Models/Overview"

const mockOverviewData: OverviewData = {
  errors: {
    count: 10,
    rate: 0.5,
  },
  count: 20,
  meanDuration: 30,
  meanTpdex: 95,
  timeRange: "1h",
  transactions: [
    {
      datetime: "2021-08-01T00:00:00Z",
      count: 10,
      errors: 3,
      cached: 0,
    },
    {
      datetime: "2021-08-01T01:00:00Z",
      count: 20,
      errors: 5,
      cached: 2,
    },
  ],
}
export default http.get("/api/overview", () => {
  return HttpResponse.json(mockOverviewData)
})
