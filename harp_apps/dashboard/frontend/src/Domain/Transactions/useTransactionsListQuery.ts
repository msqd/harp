import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"
import { Transaction } from "Models/Transaction"
import { FilterValue, Filters, MinMaxFilter } from "Types/filters"

function getQueryStringFromRecord(
  filters: Record<string, FilterValue> | { page: number; cursor?: string | null; search?: string | null },
) {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      if (Array.isArray(value)) {
        searchParams.append(key, value.toString())
      } else if (typeof value === "object") {
        const minMaxFilter = value as MinMaxFilter
        if (minMaxFilter.min !== undefined) {
          searchParams.set(`${key}min`, minMaxFilter.min.toString())
        }
        if (minMaxFilter.max !== undefined) {
          searchParams.set(`${key}max`, minMaxFilter.max.toString())
        }
      } else {
        searchParams.set(key, value.toString())
      }
    }
  }
  return searchParams.toString()
}

export function useTransactionsListQuery({
  page = 1,
  cursor = undefined,
  filters = undefined,
  search = undefined,
}: {
  filters?: Filters
  page?: number
  cursor?: string | null
  search?: string | null
}) {
  const api = useApi()
  const qs = filters
    ? getQueryStringFromRecord({ ...filters, page, cursor: page == 1 ? undefined : cursor, search })
    : ""

  return useQuery<ItemList<Transaction> & { total: number; pages: number; perPage: number }>(
    ["transactions", qs],
    () => api.fetch("/transactions" + (qs ? `?${qs}` : "")).then((r) => r.json()),
    {
      refetchInterval: 30000,
    },
  )
}
