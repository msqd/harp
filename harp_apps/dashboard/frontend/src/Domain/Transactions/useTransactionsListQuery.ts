import { useEffect, useRef } from "react"
import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"
import { Transaction } from "Models/Transaction"
import { Filters, FilterValue, MinMaxFilter } from "Types/filters"

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
  paused = false,
}: {
  paused?: boolean
  filters?: Filters
  page?: number
  cursor?: string | null
  search?: string | null
}) {
  const api = useApi()
  const qs = filters
    ? getQueryStringFromRecord({ ...filters, page, cursor: page == 1 ? undefined : cursor, search })
    : ""

  const wasPaused = useRef(paused)

  const query = useQuery<ItemList<Transaction> & { total: number; pages: number; perPage: number }>(
    ["transactions", qs],
    () => api.fetch("/transactions" + (qs ? `?${qs}` : "")).then((r) => r.json()),
    {
      refetchInterval: paused ? false : 10000,
      refetchOnWindowFocus: !paused,
      refetchOnReconnect: !paused,
    },
  )

  const { refetch } = query
  useEffect(() => {
    if (wasPaused.current && !paused) {
      void refetch()
    }
    wasPaused.current = paused
  }, [paused, refetch])

  return query
}
