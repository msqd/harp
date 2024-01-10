import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"
import { Transaction } from "Models/Transaction"
import { Filter, Filters } from "Types/filters"

function getQueryStringFromRecord(filters: Record<string, Filter> | { page: number; cursor?: string }) {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(filters) as [string, string | number | undefined][]) {
    if (value) {
      searchParams.append(key, value.toString())
    }
  }
  return searchParams.toString()
}

export function useTransactionsListQuery({
  page = 1,
  cursor = undefined,
  filters = undefined,
}: {
  filters?: Filters
  page?: number
  cursor?: string
}) {
  const api = useApi()
  const qs = filters ? getQueryStringFromRecord({ ...filters, page, cursor: page == 1 ? undefined : cursor }) : ""

  return useQuery<ItemList<Transaction> & { total: number; pages: number; perPage: number }>(
    ["transactions", qs],
    () => api.fetch("/transactions" + (qs ? `?${qs}` : "")).then((r) => r.json()),
    {
      refetchInterval: 30000,
    },
  )
}
