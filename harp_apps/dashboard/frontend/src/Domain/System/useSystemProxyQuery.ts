import { useMutation, useQuery, useQueryClient } from "react-query"

import { useApi } from "Domain/Api"

const QUERY_KEY = ["system", "proxy"]

export function useSystemProxyQuery() {
  const api = useApi()
  return useQuery<{ endpoints: Settings.Proxy.Endpoint[] }>(
    QUERY_KEY,
    () => api.fetch("/system/proxy").then((r) => r.json()),
    { refetchInterval: 5000 },
  )
}

export function useSystemProxyMutation() {
  const queryClient = useQueryClient()
  const api = useApi()
  return useMutation({
    mutationFn: (data: { endpoint: string; action: string; url: string }) =>
      api.put(`/system/proxy`, { body: JSON.stringify(data) }).then((r) => r.json()),
    onSuccess: (data) => {
      queryClient.setQueryData(QUERY_KEY, data)
    },
  })
}
