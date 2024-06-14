import { ReactNode } from "react"

import { classNames } from "ui/Utilities"

import { StyledJumboBadge, StyledJumboBadgeProps } from "./StyledJumboBadge.tsx"
import { tpdexScale } from "./constants.ts"

export default function TpdexBadge({
  score,
  className = undefined,
  children,
  ...styledProps
}: { score?: number; className?: string; children?: ReactNode } & StyledJumboBadgeProps) {
  if (score === undefined) {
    return null
  }

  for (const rating of tpdexScale) {
    if (rating.threshold === undefined || score >= rating.threshold) {
      return (
        <StyledJumboBadge
          title={`score: ${score}`}
          className={classNames(rating.className, className)}
          {...styledProps}
        >
          {rating.label}
          {children}
        </StyledJumboBadge>
      )
    }
  }

  return <StyledJumboBadge title={`score: ${score}`}>?</StyledJumboBadge>
}
