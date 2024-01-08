import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { OverviewData } from "Models/Overview"

export function useOverviewDataQuery(endpoint: string | undefined = undefined) {
  const api = useApi()
  let url = "/overview"
  if (endpoint) {
    url += `?endpoint=${encodeURIComponent(endpoint)}`
  }
  return useQuery<OverviewData>(["overview", endpoint], () => api.fetch(url).then((r) => r.json()))
}
