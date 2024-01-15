import { useMutation } from "react-query"

import { useApi } from "Domain/Api"

export interface TransactionFlagCreate {
  flagId: number
}

export function useTransactionFlagDeleteMutation() {
  const api = useApi()
  return useMutation((data: TransactionFlagCreate) =>
    api.del("/transactions/flag", { body: JSON.stringify(data) }).then((r) => r.json()),
  )
}
