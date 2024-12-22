import { CSSProperties } from "react"

import { classNames } from "ui/Utilities"

import LoadingSpinner from "./LoadingSpinner.tsx"

export default function Loader({ style, className }: { style?: CSSProperties; className?: string }) {
  return (
    <div role="status" className="w-full text-center">
      <span className={classNames(className, "inline-flex gap-4 items-center")} style={style}>
        <LoadingSpinner />
        <span>Loading...</span>
      </span>
    </div>
  )
}
