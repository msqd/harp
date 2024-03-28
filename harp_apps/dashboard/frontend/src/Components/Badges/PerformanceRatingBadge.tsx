import { StyledJumboBadge, StyledJumboBadgeProps } from "./StyledJumboBadge.tsx"
import { applicationPerformanceRatingScale } from "./constants.ts"

/**
 * Component in charge of displaying A+, A, B, C, ... performance rating badges
 */
export const PerformanceRatingBadge = ({ duration, ...styledProps }: { duration: number } & StyledJumboBadgeProps) => {
  if (duration === 0) {
    return (
      <StyledJumboBadge className="bg-gray-100" {...styledProps}>
        ?
      </StyledJumboBadge>
    )
  }

  for (const rating of applicationPerformanceRatingScale) {
    if (rating.threshold === undefined || duration <= rating.threshold) {
      return (
        <StyledJumboBadge className={rating.className} {...styledProps}>
          {rating.label}
        </StyledJumboBadge>
      )
    }
  }

  return <StyledJumboBadge {...styledProps}>?</StyledJumboBadge>
}
