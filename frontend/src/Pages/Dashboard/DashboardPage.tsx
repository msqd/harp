import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useDashboardDataQuery } from "Domain/Dashboard"

import { DashboardCharts } from "./DashboardCharts"

const DashboardPage = () => {
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

export default DashboardPage
