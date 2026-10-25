import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

import type { Role } from "./useRole.ts"

export function useSystemQuery() {
  const api = useApi()
  return useQuery<{
    version: string
    revision: string
    /** Username of the account the request acts as. */
    user?: string | null
    displayName?: string | null
    /** Role the request acts with. */
    role?: Role
  }>(["system"], () => api.fetch("/system").then((r) => r.json()))
}
