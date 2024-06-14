import { ReactNode } from "react"
import { Sparklines, SparklinesLine, SparklinesSpots } from "react-sparklines"

interface SparklineChartProps {
  data: number[]
  color: string
  children?: ReactNode
}

export function SparklineChart({ data, color, children }: SparklineChartProps) {
  return (
    <>
      {children}
      <Sparklines
        min={0}
        max={Math.max(0, ...data) + 1}
        data={data}
        style={{ margin: "-3px", position: "absolute", bottom: 0, left: 0, zIndex: 0 }}
      >
        <SparklinesLine color={color} />
        <SparklinesSpots
          spotColors={{
            "-1": color,
            "0": color,
            "1": color,
          }}
        />
      </Sparklines>
    </>
  )
}
