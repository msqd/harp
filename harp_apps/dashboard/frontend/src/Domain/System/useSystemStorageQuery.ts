import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

export function useSystemStorageQuery() {
  const api = useApi()
  return useQuery(["system", "storage"], () => api.fetch("/system/storage").then((r) => r.json()))
}
