import { useQuery } from "react-query"
import { useApi } from "Domain/Api"

export interface KeyValueSettings {
  [key: string]: string | KeyValueSettings
}

export function useProxySettingsQuery() {
  const api = useApi()
  return useQuery<KeyValueSettings>("proxySettings", () => api.fetch("/settings").then((r) => r.json()))
}
