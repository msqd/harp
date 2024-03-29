import { Sparklines, SparklinesCurve, SparklinesSpots } from "react-sparklines"

import ApdexBadge from "Components/Badges/ApdexBadge.tsx"

export function PerformancesSummary({ mean, data }: { mean: number; data: number[] }) {
  return (
    <>
      <div className="flex self-center relative z-10">
        <ApdexBadge score={mean} size="xl" className="ring-1 ring-white" />
      </div>
      <Sparklines min={0} data={data} style={{ margin: "-3px", position: "absolute", bottom: 0, left: 0, zIndex: 0 }}>
        <SparklinesCurve color="#ADD8E6" />
        <SparklinesSpots />
      </Sparklines>
    </>
  )
}
