import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts"

interface Data {
  date: string
  requests: string
  errors: string
}

interface RequestCHartProps {
  data: Data[]
  width?: string
}

export const RequestsChart: React.FC<RequestCHartProps> = ({ data, width }) => {
  return (
    <ResponsiveContainer width={width} height={300}>
      <ComposedChart
        width={400}
        height={300}
        data={data}
        margin={{
          top: 0,
          right: 0,
          left: 0,
          bottom: 0,
        }}
      >
        <CartesianGrid stroke="#f5f5f5" vertical={false} />
        <XAxis dataKey="date" interval={data.length - 2} tickLine={false} axisLine={{ stroke: "#f5f5f5" }} />
        <Tooltip isAnimationActive={false} />
        <Legend verticalAlign="top" align="right" height={36} iconSize={10} />
        <Bar
          radius={[10, 10, 0, 0]}
          dataKey="requests"
          barSize={20}
          fill="#ADD8E6"
          legendType="rect"
          name="requests"
          isAnimationActive={false}
        />
        <Line
          dot={false}
          strokeWidth={2}
          strokeLinecap="round"
          type="monotone"
          dataKey="errors"
          stroke="#FF0000"
          legendType="rect"
          name="Errors"
          isAnimationActive={false}
        />
        <YAxis tickLine={false} axisLine={{ stroke: "#f5f5f5" }} domain={[5, "dataMax + 5"]} tickCount={5} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
