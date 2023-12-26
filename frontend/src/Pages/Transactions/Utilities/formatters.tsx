import { getReasonPhrase } from "http-status-codes"
import { ReactElement } from "react"

import { Badge, BadgeColor } from "mkui/Components/Badge"

export const RequestMethodBadge = ({ method }: { method: string }) => {
  switch (method) {
    case "GET":
      return <Badge color="green">{method}</Badge>
    case "DELETE":
      return <Badge color="red">{method}</Badge>
    case "PUT":
      return <Badge color="yellow">{method}</Badge>
    case "POST":
      return <Badge color="orange">{method}</Badge>
    case "PATCH":
      return <Badge color="purple">{method}</Badge>
    case "OPTIONS":
      return <Badge color="blue">{method}</Badge>
  }
  return <Badge>{method}</Badge>
}

export const formatRequestMethod = (method: unknown) => {
  return <RequestMethodBadge method={method as string} />
}

const getStatusColorFromStatusCode = (statusCode: number): BadgeColor => {
  if (statusCode >= 200 && statusCode < 300) {
    return "green"
  }

  if (statusCode >= 300 && statusCode < 400) {
    return "blue"
  }

  if (statusCode >= 400 && statusCode < 500) {
    return "orange"
  }

  if (statusCode >= 500 && statusCode < 600) {
    return "red"
  }

  if (statusCode >= 600) {
    return "purple"
  }

  return "default"
}

export const ResponseStatusBadge = ({ statusCode }: { statusCode: number }) => {
  const color = getStatusColorFromStatusCode(statusCode)
  let reason: string

  try {
    reason = getReasonPhrase(statusCode)
  } catch (e) {
    reason = "Unknown"
  }

  return (
    <Badge color={color}>
      {statusCode} {reason}
    </Badge>
  )
}

export const durationRatingScale: { label: string; threshold?: number; className: string }[] = [
  { label: "A++", threshold: 0.025, className: "bg-teal-400" },
  { label: "A+", threshold: 0.05, className: "bg-emerald-400" },
  { label: "A", threshold: 0.1, className: "bg-green-500" },
  { label: "B", threshold: 0.25, className: "bg-lime-500" },
  { label: "C", threshold: 0.5, className: "bg-yellow-500" },
  { label: "D", threshold: 1.0, className: "bg-amber-500" },
  { label: "E", threshold: 2.0, className: "bg-orange-500" },
  { label: "F", threshold: 4.0, className: "bg-red-500" },
  { label: "G", className: "bg-red-700" },
]

export const getDurationRatingBadge = (duration: number): ReactElement => {
  for (const rating of durationRatingScale) {
    if (rating.threshold === undefined || duration <= rating.threshold) {
      return <span className={"px-1 py-0.5 text-white font-semibold " + rating.className}>{rating.label}</span>
    }
  }

  return <span className="px-1 py-0.5 text-white font-semibold">?</span>
}
