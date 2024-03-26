import { RequestMethodBadge } from "Components/Badges/RequestMethodBadge.tsx"
import { ResponseStatusBadge } from "Components/Badges/ResponseStatusBadge.tsx"
import { Badge } from "ui/Components/Badge"

interface MessageSummaryProps {
  kind?: string
  summary?: string
  endpoint?: string
}

export function MessageSummary({ kind, summary = "", endpoint }: MessageSummaryProps) {
  if (kind == "request") {
    const [method, url] = summary.split(" ")
    return (
      <span className="font-normal">
        <RequestMethodBadge method={method} />
        {endpoint ? (
          <span className="inline-flex items-center bg-gray-50 px-1 ml-2 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
            {endpoint}
          </span>
        ) : null}
        <span className="text-gray-500 font-mono text-xs">{url}</span>
      </span>
    )
  }

  if (kind == "response") {
    const splitSummary = summary.split(" ")
    return (
      <span className="font-normal">
        <ResponseStatusBadge statusCode={parseInt(splitSummary[1])} />
      </span>
    )
  }

  if (kind == "error") {
    return <Badge color="red">{summary}</Badge>
  }

  return <span className="font-normal text-gray-500 font-mono text-xs">n/a</span>
}
