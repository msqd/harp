import { useQuery } from "react-query"

import { useApi } from "Domain/Api"

interface TransactionFilter {
  values: Array<{ name: string; count?: number }>
  current: string[]
  fallbackName?: string
}

export function useTransactionsFiltersQuery() {
  const api = useApi()
  return useQuery<Record<string, TransactionFilter>>(
    "transactions/filters",
    () => api.fetch("/transactions/filters").then((r) => r.json()),
    { refetchInterval: 30000 },
  )
}
