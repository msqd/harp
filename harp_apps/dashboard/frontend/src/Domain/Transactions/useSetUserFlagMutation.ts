import { useMutation } from "react-query"

import { useApi } from "Domain/Api"

export interface TransactionFlagCreate {
  transactionId: string
  flag: "favorite"
  value: boolean
}

export function useSetUserFlagMutation() {
  const api = useApi()
  return useMutation(({ transactionId, flag, value }: TransactionFlagCreate) => {
    return (value ? api.put : api.del)(`/transactions/${transactionId}/flags/${flag}`).then((r) => r.json())
  })
}
