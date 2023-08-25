import { TransactionRequest } from "./Types"
import { useQuery } from "react-query"
import { useApi } from "Domain/Api"

export function useRequestsDetailQuery(id?: string) {
  const api = useApi()
  return useQuery<TransactionRequest | Record<string, never>>(["requests", id], () => {
    if (id) {
      return api.fetch(`/requests/${id}`).then((r) => r.json())
    }
    return {}
  })
}
