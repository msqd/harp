import { RequestsChart } from "./RequestChart"

import { H2 } from "mkui/Components/Typography"
import { DashboardGraphData } from "Models/Dashboard"
import { EndpointChart } from "./EndpointChart"

export const DashboardCharts = ({ data }: DashboardGraphData) => {
  const rating = "A"
  const endpoints = ["foo", "bar"]
  return (
    <>
      <H2>Request statuses over time</H2>
      <div style={{ display: "flex", alignItems: "center" }}>
        <div
          className={`mr-5 p-2 w-12 h-12 flex items-center justify-center border border-green-700 ${
            rating === "A" ? "bg-green-500" : rating === "B" ? "bg-yellow-500" : "bg-red-500"
          } bg-opacity-50`}
        >
          <h3 style={{ color: "green", fontSize: "24px" }}>{rating}</h3>
        </div>
        <RequestsChart data={data} width="90%"></RequestsChart>
      </div>
      <H2>Request charts per endpoint</H2>
      {endpoints.map((endpoint, index) => (
        <EndpointChart key={index} endpoint={endpoint} />
      ))}
    </>
  )
}
