import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { DevelopmentOnlySetting } from "ui/Components/DevelopmentOnlyWarning"

export function useSystemQuery() {
  const api = useApi()
  return useQuery<{
    version: string
    revision: string
    user?: string | null
    development_only_settings?: DevelopmentOnlySetting[]
  }>(["system"], () => api.fetch("/system").then((r) => r.json()))
}
