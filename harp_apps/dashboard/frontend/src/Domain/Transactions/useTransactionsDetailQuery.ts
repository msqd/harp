import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { Transaction } from "Models/Transaction"

export class TransactionNotFoundError extends Error {
  constructor(id?: string) {
    super(`Transaction ${id} not found`)
    this.name = "TransactionNotFoundError"
  }
}

export function useTransactionsDetailQuery(id?: string) {
  const api = useApi()

  return useQuery<Transaction>(
    ["transactions", "detail", id],
    async () => {
      const response = await api.fetch(`/transactions/${id}`)
      if (response.status === 404) throw new TransactionNotFoundError(id)
      if (!response.ok) throw new Error(`Unable to load transaction ${id} (${response.status})`)
      return (await response.json()) as Transaction
    },
    { enabled: !!id, retry: (count, error) => !(error instanceof TransactionNotFoundError) && count < 3 },
  )
}
