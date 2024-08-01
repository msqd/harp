import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

export function useSystemProxyQuery() {
  const api = useApi()
  return useQuery(["system/proxy"], () => api.fetch("/system/proxy").then((r) => r.json()))
}
