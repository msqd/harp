import { theme } from "twin.macro"

export const tpdexScale: { label: string; threshold?: number; className: string; bgColor: string }[] = [
  { label: "A++", threshold: 98, className: "bg-teal-400", bgColor: theme`colors.teal.400` },
  { label: "A+", threshold: 96, className: "bg-emerald-400", bgColor: theme`colors.emerald.400` },
  { label: "A", threshold: 93, className: "bg-green-500", bgColor: theme`colors.green.500` },
  { label: "B", threshold: 83, className: "bg-lime-500", bgColor: theme`colors.lime.500` },
  { label: "C", threshold: 69, className: "bg-yellow-500", bgColor: theme`colors.yellow.500` },
  { label: "D", threshold: 49, className: "bg-amber-500", bgColor: theme`colors.amber.500` },
  { label: "E", threshold: 31, className: "bg-orange-500", bgColor: theme`colors.orange.500` },
  { label: "F", threshold: 17, className: "bg-red-500", bgColor: theme`colors.red.500` },
  { label: "G", className: "bg-red-700", bgColor: theme`colors.red.700` },
]

export function getTpdexRating(score: number) {
  for (const rating of tpdexScale) {
    if (rating.threshold === undefined || score >= rating.threshold) {
      return rating
    }
  }

  throw new Error("Invalid score (but that should not happen).")
}
