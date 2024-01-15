import { useMutation } from "react-query"

import { useApi } from "Domain/Api"

export interface TransactionFlagCreate {
  transactionId: string
}

export function useTransactionFlagDeleteMutation() {
  const api = useApi()
  return useMutation((data: TransactionFlagCreate) =>
    api.del("/transactions/flag", { body: JSON.stringify(data) }).then((r) => r.json()),
  )
}
