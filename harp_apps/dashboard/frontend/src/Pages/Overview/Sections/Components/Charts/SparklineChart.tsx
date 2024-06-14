import { useWindowWidth } from "@react-hook/window-size"
import { ReactNode, useEffect, useRef, useState } from "react"
import { Sparklines, SparklinesLine, SparklinesSpots } from "react-sparklines"

interface SparklineChartProps {
  data: number[]
  color: string
  children?: ReactNode
  rightLegend?: ReactNode
  showTopHBar?: boolean
}

export function SparklineChart({ data, color, children, rightLegend, showTopHBar = false }: SparklineChartProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [height, setHeight] = useState(0)
  const windowWidth = useWindowWidth({ wait: 20 })
  useEffect(() => {
    if (ref.current) {
      const sparkline = ref.current.querySelector("svg")
      if (sparkline) {
        setHeight(sparkline.getBoundingClientRect().height)
      }
    }
  }, [ref, windowWidth])
  return (
    <div ref={ref}>
      {children}
      <Sparklines
        min={0}
        max={Math.max(0, ...data) || 1}
        data={data}
        style={{
          margin: "-3px",
          position: "absolute",
          bottom: 0,
          left: 0,
          zIndex: 0,
          borderTop: showTopHBar ? "1px dashed #E5E7EB" : "none",
        }}
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
      {rightLegend ? (
        <div className="absolute right-0 bottom-0 flex flex-col items-end" style={{ height: `${height - 3}px` }}>
          {rightLegend}
        </div>
      ) : null}
    </div>
  )
}
