import { ComponentType, ReactElement } from "react"
import { truncate } from "Utils/Strings"
import { Badge, type BadgeColor } from "mkui/Components/Badge"
import { ArrowLeftIcon, ArrowRightIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/outline"
import { getReasonPhrase } from "http-status-codes"

function createShortIdFormatter({
  maxLength = 7,
  Icon = null,
}: { maxLength?: number; Icon?: ComponentType<any> | null } = {}) {
  return (id: unknown) => {
    return (
      <span className="font-mono inline-flex items-center bg-white px-1 mx-1 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
        {Icon ? (
          <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
            <Icon className="h-3 w-3 text-gray-500" aria-hidden="true" />
          </span>
        ) : null}
        {truncate(id as string, maxLength)}
      </span>
    )
  }
}

export const formatTransactionShortId = createShortIdFormatter({ Icon: ArrowsRightLeftIcon, maxLength: 9 })
export const formatRequestShortId = createShortIdFormatter({ Icon: ArrowRightIcon, maxLength: 5 })
export const formatResponseShortId = createShortIdFormatter({ Icon: ArrowLeftIcon, maxLength: 5 })
export const formatRequestMethod = (method: unknown) => {
  switch (method) {
    case "GET":
      return <Badge color="green">{method}</Badge>
  }
  return <Badge color="default">{method as string}</Badge>
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
export const formatStatus = (statusCode: number): ReactElement => {
  const color = getStatusColorFromStatusCode(statusCode)

  return (
    <Badge color={color}>
      {statusCode} {getReasonPhrase(statusCode)}
    </Badge>
  )
}
