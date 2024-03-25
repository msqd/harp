import { ReactNode } from "react"

interface FacetLabelProps {
  name: string
  count?: number

  children?: ReactNode
}

export function FacetLabel({ name, count = undefined, children = undefined }: FacetLabelProps) {
  return (
    <div>
      {name}
      {count ? <span className={"text-xs text-gray-400"}> ({count})</span> : null}
      {children ?? null}
    </div>
  )
}
