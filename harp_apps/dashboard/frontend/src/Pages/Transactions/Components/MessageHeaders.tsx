import { useBlobQuery } from "Domain/Transactions/useBlobQuery.ts"

interface MessageHeadersProps {
  id: string
}

export function MessageHeaders({ id }: MessageHeadersProps) {
  const query = useBlobQuery(id)

  if (query && query.isSuccess && query.data !== undefined) {
    return (
      <table className="mb-2 w-full text-xs font-mono">
        <tbody>
          {query.data.content.split("\n").map((line, index) => {
            const s = line.split(":", 2)
            return (
              <tr key={index}>
                <td className="px-2 w-1 text-blue-600 truncate">{s[0]}</td>
                <td className="px-2 whitespace-nowrap">{s[1]}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    )
  }
}
