import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { ReactNode, useState } from "react"

import { H5 } from "ui/Components/Typography"
import { classNames } from "ui/Utilities"

interface FoldableProps {
  open?: boolean
  title: ReactNode
  subtitle?: ReactNode
  children?: ReactNode
  className?: string
}

export function Foldable({ open = true, title, subtitle, children = undefined, className }: FoldableProps) {
  const [isOpen, setIsOpen] = useState(open)

  return (
    <div className={classNames(className, "px-4 py-3")}>
      <H5
        padding="pt-0"
        className={classNames("flex w-full whitespace-nowrap", children ? "cursor-pointer" : null)}
        onClick={() => setIsOpen(!isOpen)}
      >
        {/* title (clickable) */}
        <div className="grow font-normal truncate">
          <span className="font-semibold">{title}</span>
        </div>

        {/* control to fold/unfold the content */}
        {children ? (
          isOpen ? (
            <ChevronUpIcon className="h-4 w-4 min-w-4 text-gray-600" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 min-w-4 text-gray-600" />
          )
        ) : null}
      </H5>
      {subtitle ?? null}
      {/* actual foldable content */}
      {children ? (
        <div className={"mt-2 space-y-2 overflow-x-auto " + (isOpen ? "" : "hidden")}> {children}</div>
      ) : null}
    </div>
  )
}
