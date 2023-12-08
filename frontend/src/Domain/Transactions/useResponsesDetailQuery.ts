import { TransactionResponse } from "./OldDeprecatedTypes"
import { useQuery } from "react-query"
import { useApi } from "Domain/Api"

export function useResponsesDetailQuery(id?: string) {
  const api = useApi()
  return useQuery<TransactionResponse | Record<string, never>>(["responses", id], () => {
    if (id) {
      return api.fetch(`/responses/${id}`).then((r) => r.json())
    }
    return {}
  })
}
