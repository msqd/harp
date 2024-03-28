import { useBlobQuery } from "Domain/Transactions/useBlobQuery.ts"

import { PrettyBody } from "./PrettyBody.tsx"

export function MessageBody({ id }: { id: string }) {
  const query = useBlobQuery(id)

  if (query && query.isSuccess && query.data !== undefined) {
    if (query.data.content.length) {
      return (
        <div className="px-2">
          <PrettyBody content={query.data.content} contentType={query.data.contentType} />
        </div>
      )
    }
  }

  return null
}
