import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

export interface SummaryData {
  tpdex: { mean: number; data: { datetime: string; value: number }[] }
  transactions: { rate: number; period: string; data: { datetime: string; value: number }[] }
  errors: { rate: number; period: string; data: { datetime: string; value: number }[] }
}

export function useSummaryDataQuery() {
  const api = useApi()
  return useQuery<SummaryData>(["overview", "summary"], () => api.fetch("/overview/summary").then((r) => r.json()))
}
