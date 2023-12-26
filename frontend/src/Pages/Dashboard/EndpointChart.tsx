import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useDashboardEndpointQuery } from "Domain/Dashboard"

import { RequestsChart } from "./RequestChart"

interface EndpointChartProps {
  endpoint: string
}

export const EndpointChart = ({ endpoint }: EndpointChartProps) => {
  const query = useDashboardEndpointQuery(endpoint)

  return (
    <OnQuerySuccess query={query}>
      {(query) => {
        return <RequestsChart data={query.data.data} />
      }}
    </OnQuerySuccess>
  )
}
