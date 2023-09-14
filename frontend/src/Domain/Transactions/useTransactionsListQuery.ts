import { useQuery } from "react-query"
import { Transaction } from "./Types"
import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"

export function useTransactionsListQuery() {
  const api = useApi()
  return useQuery<ItemList<Transaction>>("transactions", () => api.fetch("/transactions").then((r) => r.json()), {
    refetchInterval: 10000,
  })
}
