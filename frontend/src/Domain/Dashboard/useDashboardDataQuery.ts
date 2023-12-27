import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { DashboardGraphData } from "Models/Dashboard.ts"

export function useDashboardDataQuery() {
  const api = useApi()
  return useQuery<DashboardGraphData>("dashboard", () => api.fetch("/dashboard").then((r) => r.json()))
}
