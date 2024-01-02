import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

export function useSystemDependenciesQuery() {
  const api = useApi()
  return useQuery<{ python: Array<string> }>(["system", "dependencies"], () =>
    api.fetch("/system/dependencies").then((r) => r.json()),
  )
}
