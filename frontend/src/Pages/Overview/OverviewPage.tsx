import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useDashboardDataQuery } from "Domain/Overview"

import { TransactionsOverview } from "./OverviewCharts"
import { TransactionsOverviewChart } from "./Components/OverviewChart/TransactionsOverviewChart"

export const OverviewPage = () => {
  const query = useDashboardDataQuery()
  const endpoints = ["foo", "bar", "foo"]

  return (
    <Page title="Overview" description="Useful insights">
      <OnQuerySuccess query={query} queries={[query, query]}>
        {(query) => {
          return <TransactionsOverviewChart data={query.data} title="Transactions Overview" className="mb-10" />
        }}
      </OnQuerySuccess>

      <div className="grid grid-cols-2 gap-4">
        {endpoints.map((endpoint, index) => (
          <TransactionsOverview key={index} endpoint={endpoint} title={endpoint} className="border p-2" />
        ))}
      </div>
    </Page>
  )
}
