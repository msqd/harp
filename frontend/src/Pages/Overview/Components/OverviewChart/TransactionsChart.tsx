import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { format } from "date-fns"

interface RequestCHartProps {
  data: Array<{ date: string; transactions: number; errors: number }>
  width?: string
}

export const TransactionsChart: React.FC<RequestCHartProps> = ({ data, width }) => {
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
          dataKey="date"
          tickLine={false}
          axisLine={{ stroke: "#f5f5f5" }}
          interval={"preserveStartEnd"}
          fontSize={12}
        />
        <Tooltip isAnimationActive={false} filterNull={false} />
        <Legend verticalAlign="top" align="right" height={36} iconSize={10} />
        <Bar
          dataKey="transactions"
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
          stroke="#FF0000"
          legendType="circle"
          name="Errors"
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
