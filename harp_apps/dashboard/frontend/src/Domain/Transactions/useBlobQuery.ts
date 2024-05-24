import { useQuery } from "react-query"

import { useApi } from "../Api"

interface Blob {
  id: string
  content: ArrayBuffer
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
        content: buffer,
        contentType: response.headers.get("Content-Type"),
      } as Blob
    }
  })
}
