import { useQuery } from "react-query"
import { useApi } from "Domain/Api"

export function useDashboardDataQuery() {
  const api = useApi()
  return useQuery("dashboard", () => api.fetch("/dashboard").then((r) => r.json()))
}
