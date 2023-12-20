import { useQuery } from "react-query"
import { useApi } from "Domain/Api"

export function useSystemQuery() {
  const api = useApi()
  return useQuery<{
    version: string
    revision: string
    user?: string | null
  }>(["system"], () => api.fetch("/system").then((r) => r.json()))
}
