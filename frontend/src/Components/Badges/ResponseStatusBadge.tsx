import { getReasonPhrase } from "http-status-codes"

import { Badge, BadgeColor } from "mkui/Components/Badge"

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
