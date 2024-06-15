import { ReactNode } from "react"

import { classNames } from "ui/Utilities"

import { StyledJumboBadge, StyledJumboBadgeProps } from "./StyledJumboBadge.tsx"
import { getTpdexRating } from "./constants.ts"

export default function TpdexBadge({
  score,
  className = undefined,
  children,
  ...styledProps
}: { score?: number; className?: string; children?: ReactNode } & StyledJumboBadgeProps) {
  if (score === undefined) {
    return null
  }

  const rating = getTpdexRating(score)

  return (
    <StyledJumboBadge title={`score: ${score}`} className={classNames(rating.className, className)} {...styledProps}>
      {rating.label}
      {children}
    </StyledJumboBadge>
  )
}
