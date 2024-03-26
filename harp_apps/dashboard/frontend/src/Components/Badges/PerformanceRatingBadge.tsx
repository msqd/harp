import { applicationPerformanceRatingScale } from "./constants.ts"

/**
 * Component in charge of displaying A+, A, B, C, ... performance rating badges
 */
export const PerformanceRatingBadge = ({ duration }: { duration: number }) => {
  if (duration === 0) {
    return <span className="px-1 py-0.5 text-white font-semibold bg-gray-100">?</span>
  }

  for (const rating of applicationPerformanceRatingScale) {
    if (rating.threshold === undefined || duration <= rating.threshold) {
      return <span className={"px-1 py-0.5 text-white font-semibold " + rating.className}>{rating.label}</span>
    }
  }

  return <span className="px-1 py-0.5 text-white font-semibold">?</span>
}
