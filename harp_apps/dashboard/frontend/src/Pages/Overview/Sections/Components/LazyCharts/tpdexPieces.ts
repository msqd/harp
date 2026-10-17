import { tpdexScale } from "Components/Badges/constants.ts"

export const tpdexPieces = () =>
  tpdexScale.map((rating, i) => ({
    label: rating.label,
    color: rating.bgColor,
    ...(i > 0 && { lt: tpdexScale[i - 1].threshold }),
    ...(rating.threshold !== undefined && { gte: rating.threshold }),
  }))
