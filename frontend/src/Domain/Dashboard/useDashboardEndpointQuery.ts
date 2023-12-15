import { useQuery } from "react-query"
import { useApi } from "Domain/Api"
import { DashboardGraphData } from "Models/Dashboard.ts"

export function useDashboardEndpointQuery(endpoint: string) {
  const api = useApi()
  return useQuery<DashboardGraphData>(["dashboard", endpoint], () =>
    api.fetch(`/dashboard/${endpoint}`).then((r) => r.json()),
  )
}
