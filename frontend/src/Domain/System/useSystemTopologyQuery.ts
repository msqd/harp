import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

export function useSystemTopologyQuery() {
  const api = useApi()
  return useQuery<unknown>(["system", "topology"], () => api.fetch("/system/topology").then((r) => r.json()))
}
