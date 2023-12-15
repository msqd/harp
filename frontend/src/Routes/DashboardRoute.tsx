import tw, { styled, theme } from "twin.macro"
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart } from "recharts"
import colors from "tailwindcss/colors"

import { H1, H2 } from "mkui/Components/Typography"

const data = [
  { date: "2022-01-01", requests: 120, errors: 20 },
  { date: "2022-01-02", requests: 160, errors: 30 },
  { date: "2022-01-03", requests: 200, errors: 40 },
  { date: "2022-01-04", requests: 100, errors: 50 },
  { date: "2022-01-05", requests: 280, errors: 60 },
  { date: "2022-01-06", requests: 320, errors: 70 },
  { date: "2022-01-07", requests: 300, errors: 50 },
  { date: "2022-01-08", requests: 400, errors: 90 },
  { date: "2022-01-09", requests: 440, errors: 50 },
  { date: "2022-01-10", requests: 480, errors: 50 },
  { date: "2022-01-11", requests: 300, errors: 120 },
  { date: "2022-01-12", requests: 560, errors: 130 },
  { date: "2022-01-13", requests: 600, errors: 10 },
  { date: "2022-01-14", requests: 640, errors: 150 },
  { date: "2022-01-15", requests: 680, errors: 50 },
  { date: "2022-01-16", requests: 500, errors: 170 },
  { date: "2022-01-17", requests: 760, errors: 180 },
  { date: "2022-01-18", requests: 800, errors: 190 },
  { date: "2022-01-19", requests: 400, errors: 50 },
  { date: "2022-01-20", requests: 880, errors: 210 },
  { date: "2022-01-21", requests: 300, errors: 50 },
  { date: "2022-01-22", requests: 300, errors: 50 },
  { date: "2022-01-23", requests: 1000, errors: 50 },
  { date: "2022-01-24", requests: 500, errors: 50 },
]


const PageContent = styled.main(() => [tw`py-8`])

function DashboardRoute() {
  return (
    <PageContent>
      <H2>Request statuses over time</H2>
      <ResponsiveContainer width="100%" height={300}>
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
          <YAxis
            tickLine={false}
            axisLine={{ stroke: "#f5f5f5" }}
            domain={[5, "dataMax + 5"]}
            tickCount={5}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </PageContent>
  )
}

export { DashboardRoute }
