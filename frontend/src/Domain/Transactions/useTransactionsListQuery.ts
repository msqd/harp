import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"
import { Transaction } from "Models/Transaction"
import { Filter, Filters } from "Types/filters"

function getQueryStringFromRecord(filters: Record<string, Filter> | { page: number; cursor?: string }) {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(filters)) {
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
  const qs = filters ? getQueryStringFromRecord({ ...filters, page, cursor }) : ""

  return useQuery<ItemList<Transaction>>(
    ["transactions", filters, page, cursor],
    () => api.fetch("/transactions" + (qs ? `?${qs}` : "")).then((r) => r.json()),
    {
      refetchInterval: 30000,
    },
  )
}
