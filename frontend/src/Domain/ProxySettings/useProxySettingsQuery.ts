import { useQuery } from "react-query"
import { useApi } from "Domain/Api"

export function useProxySettingsQuery() {
  const api = useApi()
  return useQuery("proxySettings", () => api.fetch("/settings").then((r) => r.json()))
}
