import { useDashboardDataQuery } from "Domain/Dashboard"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { Page } from "Components/Page"
import { DashboardCharts } from "./DashboardCharts"

const Dashboard = () => {
  const query = useDashboardDataQuery()

  return (
    <Page title="Dashboard" description="Useful insights">
      <OnQuerySuccess query={query}>
        {(query) => {
          return <DashboardCharts data={query.data.data} />
        }}
      </OnQuerySuccess>
    </Page>
  )
}

export default Dashboard
