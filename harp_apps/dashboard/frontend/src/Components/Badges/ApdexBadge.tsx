import { classNames } from "ui/Utilities"

import { StyledJumboBadge, StyledJumboBadgeProps } from "./StyledJumboBadge.tsx"
import { apdexScale } from "./constants.ts"

export default function ApdexBadge({
  score,
  className = undefined,
  ...styledProps
}: { score?: number; className?: string } & StyledJumboBadgeProps) {
  if (score === undefined) {
    return null
  }

  for (const rating of apdexScale) {
    if (rating.threshold === undefined || score >= rating.threshold) {
      return (
        <StyledJumboBadge
          title={`score: ${score}`}
          className={classNames(rating.className, className)}
          {...styledProps}
        >
          {rating.label}
        </StyledJumboBadge>
      )
    }
  }

  return <StyledJumboBadge title={`score: ${score}`}>?</StyledJumboBadge>
}
