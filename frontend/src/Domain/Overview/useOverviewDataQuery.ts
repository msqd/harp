import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { OverviewData } from "Models/Overview"

export function useOverviewDataQuery(entrypoint: string | undefined = undefined) {
  const api = useApi()
  return useQuery<OverviewData>(["overview", entrypoint], () =>
    api.fetch(entrypoint ? `/overview/${entrypoint}` : "/overview").then((r) => r.json()),
  )
}
