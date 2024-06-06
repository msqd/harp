import { useBlobQuery } from "Domain/Transactions/useBlobQuery.ts"

import { NoCacheIcon } from "./Duration.tsx"

interface MessageHeadersProps {
  id: string
}

export function MessageHeaders({ id }: MessageHeadersProps) {
  const query = useBlobQuery(id)
  const decoder = new TextDecoder("utf-8")

  if (query && query.isSuccess && query.data !== undefined) {
    return (
      <table className="mb-2 w-full text-xs font-mono">
        <tbody>
          {decoder
            .decode(query.data.content)
            .split("\n")
            .map((line, index) => {
              const s = line.split(":", 2)
              return (
                <tr key={index}>
                  <td className="px-2 w-1 text-blue-600 truncate">{s[0]}</td>
                  <td className="px-2 whitespace-nowrap">
                    {s[0].toLowerCase() == "cache-control" && s[1].toLowerCase().includes("no-cache") ? (
                      <span className="h-4 flex text-xs" title="Cache was bypassed.">
                        <NoCacheIcon />
                        {s[1]}
                      </span>
                    ) : (
                      s[1]
                    )}
                  </td>
                </tr>
              )
            })}
        </tbody>
      </table>
    )
  }
}
