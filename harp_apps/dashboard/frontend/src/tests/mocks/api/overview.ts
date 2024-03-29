import { http, HttpResponse } from "msw"
import { OverviewData } from "Models/Overview"

const mockOverviewData: OverviewData = {
  errors: {
    count: 10,
    rate: 0.5,
  },
  count: 20,
  meanDuration: 30,
  meanApdex: 95,
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
export default http.get("/api/overview", () => {
  return HttpResponse.json(mockOverviewData)
})
