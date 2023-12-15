import { useApi } from "../Api"
import { useQuery } from "react-query"

export function useBlobQuery(id?: string) {
  const api = useApi()
  return useQuery<string | null>(["blobs", id], () => {
    if (id) {
      return api
        .fetch(`/blobs/${id}`)
        .then((response) => response.arrayBuffer())
        .then((buffer) => {
          const decoder = new TextDecoder("utf-8")
          return decoder.decode(buffer)
        })
    }
    return null
  })
}
