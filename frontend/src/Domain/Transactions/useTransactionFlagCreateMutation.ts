import { useMutation } from "react-query"

import { useApi } from "Domain/Api"

export interface TransactionFlagCreate {
  transactionId?: string
  flag: number
}

export function useTransactionFlagCreateMutation() {
  const api = useApi()
  return useMutation((data: TransactionFlagCreate) =>
    api.put("/transactions/flag", { body: JSON.stringify(data) }).then((r) => r.json()),
  )
}
