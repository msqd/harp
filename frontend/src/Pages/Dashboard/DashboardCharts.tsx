import tw, { styled } from "twin.macro"
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts"

import { H1, H2 } from "mkui/Components/Typography"

const PageContent = styled.main(() => [tw`py-8`])

export const DashboardCharts = ({ data }) => {
  const rating = "A"

  console.log(data)
  return (
    <PageContent>
      <H2>Request statuses over time</H2>
      <div style={{ display: "flex", alignItems: "center" }}>
        <div
          className={`mr-5 p-2 w-12 h-12 flex items-center justify-center border border-green-700 ${
            rating === "A" ? "bg-green-500" : rating === "B" ? "bg-yellow-500" : "bg-red-500"
          } bg-opacity-50`}
        >
          <h3 style={{ color: "green", fontSize: "24px" }}>{rating}</h3>
        </div>
        <ResponsiveContainer width="90%" height={300}>
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
            <Tooltip />
            <Legend verticalAlign="top" align="right" height={36} />
            <Bar
              radius={[10, 10, 0, 0]}
              dataKey="requests"
              barSize={20}
              fill="#ADD8E6"
              legendType="rect"
              name="requests"
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
            />
            <YAxis tickLine={false} axisLine={{ stroke: "#f5f5f5" }} domain={[5, "dataMax + 5"]} tickCount={5} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </PageContent>
  )
}
