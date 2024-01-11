import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { Transaction } from "Models/Transaction"

export function useTransactionsDetailQuery(id?: string) {
  const api = useApi()

  return useQuery<Transaction>(
    ["transactions", "detail", id],
    () => api.fetch(`/transactions/${id}`).then((r) => r.json()),
    { enabled: !!id },
  )
}
