import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"
import { Transaction } from "Models/Transaction"
import { Filters } from "Types/filters"

function getQueryStringFromRecord(filters: Filters) {
  const searchParams = new URLSearchParams()
  // todo handle "*" ?
  for (const [key, value] of Object.entries(filters)) {
    console.log(key, value)
    if (value) {
      searchParams.append(key, value.toString())
    }
  }
  return searchParams.toString()
}

export function useTransactionsListQuery({ filters = undefined }: { filters?: Filters }) {
  const api = useApi()
  const qs = filters ? getQueryStringFromRecord(filters) : ""

  return useQuery<ItemList<Transaction>>(
    ["transactions", filters],
    () => api.fetch("/transactions" + (qs ? `?${qs}` : "")).then((r) => r.json()),
    {
      refetchInterval: 30000,
    },
  )
}
