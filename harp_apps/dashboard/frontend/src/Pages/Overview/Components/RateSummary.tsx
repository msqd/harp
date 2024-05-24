import { Sparklines, SparklinesLine, SparklinesSpots } from "react-sparklines"

import { StyledJumboBadge } from "Components/Badges/StyledJumboBadge.tsx"
import { classNames } from "ui/Utilities"

export function RateSummary({
  rate,
  period,
  data,
  color,
  badgeClassName = undefined,
}: {
  rate: number
  period: string
  data: number[]
  color: string
  badgeClassName?: string
}) {
  return (
    <>
      <div className="flex self-center relative z-10">
        <StyledJumboBadge className={classNames("bg-white ring-1", badgeClassName)} size="xl" color="black">
          {rate} <span className="font-light">/{period}</span>
        </StyledJumboBadge>
      </div>
      <Sparklines min={0} data={data} style={{ margin: "-3px", position: "absolute", bottom: 0, left: 0 }}>
        <SparklinesLine color={color} />
        <SparklinesSpots />
      </Sparklines>
    </>
  )
}
