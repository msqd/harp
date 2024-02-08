import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { OverviewData } from "Models/Overview"

export function useOverviewDataQuery(
  endpoint: string | undefined = undefined,
  timeRange: string | undefined = undefined,
) {
  const api = useApi()
  let url = "/overview"
  const params = new URLSearchParams()

  if (endpoint) {
    params.append("endpoint", endpoint)
  }

  if (timeRange) {
    params.append("timeRange", timeRange)
  }

  if (params.toString()) {
    url += `?${params.toString()}`
  }
  console.log(url)
  return useQuery<OverviewData>(["overview", endpoint, timeRange], () => api.fetch(url).then((r) => r.json()))
}
