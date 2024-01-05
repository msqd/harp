import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { DahsboardData } from "Models/Dashboard.ts"

export function useDashboardDataQuery(entrypoint: string | undefined = undefined) {
  const api = useApi()
  return useQuery<DahsboardData>(["dashboard", entrypoint], () =>
    api.fetch(entrypoint ? `/dashboard/${entrypoint}` : "/dashboard").then((r) => r.json()),
  )
}
