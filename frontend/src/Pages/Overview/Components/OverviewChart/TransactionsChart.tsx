import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

interface RequestCHartProps {
  data: Array<{ datetime: string; count: number; errors: number }>
  timeRange?: string
  width?: string
}

export const TransactionsChart: React.FC<RequestCHartProps> = ({ data, timeRange, width }) => {
  const tickFormatter = (tick: string) => {
    const date = new Date(tick)
    switch (timeRange) {
      case "24h":
        // If time range is 24 hours, return time in 'HH:mm' format
        return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
      case "7d":
        // If time range is 7 days, return short weekday, month, and day
        return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })
      case "1m":
        // If time range is 1 month, return short month and day
        return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
      case "1y":
        // If time range is 1 year, return month and full year
        return date.toLocaleDateString(undefined, { month: "short", year: "numeric" })
      default:
        // By default return full date
        return date.toLocaleDateString()
    }
  }

  const toolTipLabelFormatter = (label: string) => {
    const date = new Date(label)
    return date.toLocaleString()
  }

  return (
    <ResponsiveContainer width={width} height={300}>
      <ComposedChart
        width={400}
        height={300}
        data={data}
        margin={{
          top: 0,
          right: 30,
          left: 0,
          bottom: 0,
        }}
      >
        <CartesianGrid stroke="#f5f5f5" vertical={false} />
        <XAxis
          dataKey="datetime"
          tickLine={false}
          axisLine={{ stroke: "#f5f5f5" }}
          interval={"equidistantPreserveStart"}
          fontSize={12}
          tickFormatter={tickFormatter}
          minTickGap={20}
        />
        <Tooltip isAnimationActive={false} filterNull={false} labelFormatter={toolTipLabelFormatter} />
        <Legend verticalAlign="top" align="right" height={36} iconSize={10} />
        <Bar
          dataKey="count"
          barSize={20}
          fill="#ADD8E6"
          legendType="circle"
          name="transactions"
          isAnimationActive={false}
        />
        <Line
          dot={false}
          strokeWidth={2}
          strokeLinecap="round"
          type="monotone"
          dataKey="errors"
          stroke="#FF8080"
          legendType="circle"
          name="Errors (5xx)"
          isAnimationActive={false}
        />
        <YAxis
          tickLine={false}
          axisLine={{ stroke: "#f5f5f5" }}
          domain={[5, "dataMax + 5"]}
          tickCount={5}
          fontSize={12}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
