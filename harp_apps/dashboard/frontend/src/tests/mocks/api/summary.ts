import { http, HttpResponse } from "msw"
import { SummaryData } from "Domain/Overview/useSummaryDataQuery.tsx"

const mockSummaryData: SummaryData = {
  tpdex: {
    mean: 100,
    data: [...Array(24).keys()].map((i) => ({
      datetime: new Date(Date.now() - 3600 * 1000 * (24 - i)).toISOString(),
      value: 100 - ((i * i * 97) % 20),
    })),
  },
  transactions: {
    rate: 56,
    period: "min",
    data: [...Array(24).keys()].map((i) => ({
      datetime: new Date(Date.now() - 3600 * 1000 * (24 - i)).toISOString(),
      value: 56 - 10 + ((i * i * 97) % 20),
    })),
  },
  errors: {
    rate: 11,
    period: "min",
    data: [...Array(24).keys()].map((i) => ({
      datetime: new Date(Date.now() - 3600 * 1000 * (24 - i)).toISOString(),
      value: 11 - 5 + ((i * i * 97) % 10),
    })),
  },
}

export default http.get("/api/overview/summary", () => {
  return HttpResponse.json(mockSummaryData)
})
