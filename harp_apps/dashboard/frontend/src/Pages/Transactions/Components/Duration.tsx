import { XMarkIcon } from "@heroicons/react/16/solid"
import { CircleStackIcon } from "@heroicons/react/24/outline"
import { formatDuration } from "date-fns"

import TpdexBadge from "Components/Badges/TpdexBadge.tsx"
import { classNames } from "ui/Utilities"

export function NoCacheIcon() {
  return (
    <span className="h-4 w-4 relative">
      <CircleStackIcon className="absolute" />
      <XMarkIcon className="absolute" />
    </span>
  )
}

export const Duration = ({
  duration,
  tpdex,
  cached = false,
  noCache = false,
  verbose = false,
  className = undefined,
}: {
  duration: number | null
  tpdex: number | null
  cached?: boolean
  noCache?: boolean
  verbose?: boolean
  className?: string
}) => {
  if (duration !== null) {
    return (
      <div className={classNames("flex gap-x-0.5 items-center font-normal", className)}>
        {tpdex !== null ? <TpdexBadge score={tpdex} /> : null}
        <span>{formatDuration({ seconds: duration })}</span>
        {cached ? (
          <span className="h-4 flex text-xs text-slate-800" title="Response was cached.">
            <CircleStackIcon />
            {verbose ? "Cached" : null}
          </span>
        ) : null}
        {noCache ? (
          <span className="h-4 flex text-xs text-red-800" title="Cache was bypassed.">
            <NoCacheIcon />
            {verbose ? "Bypassed" : null}
          </span>
        ) : null}
      </div>
    )
  }
  return null
}
