import { useRef } from "react"

import { useBlobQuery } from "Domain/Transactions/useBlobQuery.ts"
import CopyToClipboard from "ui/Components/CopyToClipBoard/CopyToClipboard.tsx"

import { PrettyBody } from "./PrettyBody.tsx"

export function MessageBody({ id }: { id: string }) {
  const query = useBlobQuery(id)
  const ref = useRef<HTMLDivElement>(null)

  if (query && query.isSuccess && query.data !== undefined) {
    if (query.data.content.byteLength) {
      return (
        <div>
          <CopyToClipboard targetRef={ref} contentType="html" className="absolute right-2" />

          <div className="px-2 pt-4" ref={ref}>
            <PrettyBody content={query.data.content} contentType={query.data.contentType} />
          </div>
        </div>
      )
    }
  }

  return null
}
