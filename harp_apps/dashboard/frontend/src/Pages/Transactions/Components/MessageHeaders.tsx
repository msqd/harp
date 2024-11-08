import { useRef } from "react"

import { useBlobQuery } from "Domain/Transactions/useBlobQuery.ts"
import CopyToClipboard from "ui/Components/CopyToClipBoard/CopyToClipboard.tsx"

import { NoCacheIcon } from "./Duration.tsx"

interface MessageHeadersProps {
  id: string
}

export function MessageHeaders({ id }: MessageHeadersProps) {
  const query = useBlobQuery(id)
  const decoder = new TextDecoder("utf-8")
  const ref = useRef<HTMLTableElement>(null)

  if (query && query.isSuccess && query.data !== undefined) {
    return (
      <div className="flex space-y-2">
        <CopyToClipboard
          targetRef={ref}
          contentType="text/html"
          className="absolute right-2"
          description="copy headers"
        />
        <div ref={ref} className="pt-4">
          <table className="mb-2 w-full text-xs font-mono">
            <tbody>
              {decoder
                .decode(query.data.content)
                .split("\n")
                .map((line, index) => {
                  const s = line.split(":", 2)
                  const headerName = s[0]
                  const headerValue = s[1] ? line.substring(headerName.length + 1).trim() : "" // Ensures the full value after the first colon
                  return (
                    <tr key={index}>
                      <td className="px-2 w-1 text-blue-600 truncate">{headerName}</td>
                      <td className="px-2 whitespace-nowrap">
                        {headerName.toLowerCase() === "cache-control" &&
                        headerValue.toLowerCase().includes("no-cache") ? (
                          <span className="h-4 flex text-xs" title="Cache was bypassed.">
                            <NoCacheIcon />
                            {headerValue}
                          </span>
                        ) : (
                          headerValue
                        )}
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      </div>
    )
  }
}
