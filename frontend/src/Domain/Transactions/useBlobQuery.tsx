import { useQuery } from "react-query"

import { useApi } from "../Api"

const decoder = new TextDecoder("utf-8")

interface Blob {
  id: string
  content: string
  contentType?: string
}

export function useBlobQuery(id?: string) {
  const api = useApi()
  return useQuery<Blob | undefined>(["blobs", id], async () => {
    if (id) {
      const response = await api.fetch(`/blobs/${id}`)
      const buffer = await response.arrayBuffer()

      return {
        id,
        content: decoder.decode(buffer),
        contentType: response.headers.get("Content-Type"),
      } as Blob
    }
  })
}
