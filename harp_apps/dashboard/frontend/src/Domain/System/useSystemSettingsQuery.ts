import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

export interface KeyValueSettings {
  [key: string]: Setting
}

export type Setting = string | number | boolean | null | KeyValueSettings | Array<Setting>

export function useSystemSettingsQuery() {
  const api = useApi()
  return useQuery<KeyValueSettings>(["system", "settings"], () => api.fetch("/system/settings").then((r) => r.json()))
}
