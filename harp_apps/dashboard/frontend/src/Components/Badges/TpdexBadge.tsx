import { classNames } from "ui/Utilities"

import { StyledJumboBadge, StyledJumboBadgeProps } from "./StyledJumboBadge.tsx"
import { tpdexScale } from "./constants.ts"

export default function TpdexBadge({
  score,
  className = undefined,
  ...styledProps
}: { score?: number; className?: string } & StyledJumboBadgeProps) {
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
        </StyledJumboBadge>
      )
    }
  }

  return <StyledJumboBadge title={`score: ${score}`}>?</StyledJumboBadge>
}
