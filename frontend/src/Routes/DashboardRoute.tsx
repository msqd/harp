import tw, { styled, theme } from "twin.macro"
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts"
import colors from "tailwindcss/colors"

import { H1, H2 } from "mkui/Components/Typography"

const data = [
  {
    name: "5 days ago",
    "1xx": 2400,
    "2xx": 2400,
    "3xx": 2400,
    "4xx": 4000,
    "5xx": 4000,
    misc: 4000,
    default: 4000,
    ui: 4000,
    geo: 4000,
  },
  {
    name: "4 days ago",
    "1xx": 2400,
    "2xx": 2400,
    "3xx": 2400,
    "4xx": 4000,
    "5xx": 4000,
    misc: 4000,
    default: 4000,
    ui: 4000,
    geo: 4000,
  },
  {
    name: "3 days ago",
    "1xx": 2400,
    "2xx": 2400,
    "3xx": 2400,
    "4xx": 4000,
    "5xx": 4000,
    misc: 4000,
    default: 4000,
    ui: 4000,
    geo: 4000,
  },
  {
    name: "2 days ago",
    "1xx": 2400,
    "2xx": 2400,
    "3xx": 2400,
    "4xx": 4000,
    "5xx": 4000,
    misc: 4000,
    default: 4000,
    ui: 4000,
    geo: 4000,
  },
  {
    name: "yesterday",
    "1xx": 2400,
    "2xx": 2400,
    "3xx": 2400,
    "4xx": 4000,
    "5xx": 4000,
    misc: 4000,
    default: 4000,
    ui: 4000,
    geo: 4000,
  },
  {
    name: "today",
    "1xx": 2400,
    "2xx": 2400,
    "3xx": 2400,
    "4xx": 4000,
    "5xx": 4000,
    misc: 4000,
    default: 4000,
    ui: 4000,
    geo: 4000,
  },
]

const PageContent = styled.main(() => [tw`py-8`])

function DashboardRoute() {
  return (
    <PageContent>
      <H2>Request statuses over time</H2>
      <BarChart
        width={500}
        height={300}
        data={data}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="1xx" stackId="a" fill={theme("colors.slate.300")} />
        <Bar dataKey="2xx" stackId="a" fill={colors.lime["300"]} />
        <Bar dataKey="3xx" stackId="a" fill={colors.blue["300"]} />
        <Bar dataKey="4xx" stackId="a" fill={colors.amber["300"]} />
        <Bar dataKey="5xx" stackId="a" fill={colors.red["300"]} />
        <Bar dataKey="misc" stackId="a" fill={colors.fuchsia["300"]} />
      </BarChart>
      <H1>Request by route over time</H1>
      <BarChart
        width={500}
        height={300}
        data={data}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="default" stackId="a" fill={theme("colors.slate.300")} />
        <Bar dataKey="ui" stackId="a" fill={colors.lime["300"]} />
        <Bar dataKey="geo" stackId="a" fill={colors.blue["300"]} />
      </BarChart>
    </PageContent>
  )
}

export { DashboardRoute }
