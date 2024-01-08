import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useOverviewDataQuery } from "Domain/Overview"
import { useSystemSettingsQuery } from "Domain/System"

import { TransactionsOverviewChart } from "./Components/OverviewChart/TransactionsOverviewChart"
import { TransactionsOverview } from "./OverviewCharts"

export const OverviewPage = () => {
  const query = useOverviewDataQuery()
  const settingsQuery = useSystemSettingsQuery()
  interface ProxyData {
    endpoints?: { name: string; port: number; url: string; description?: string }[]
  }

  return (
    <Page title="Overview" description="Useful insights">
      <OnQuerySuccess query={query}>
        {(query) => {
          return <TransactionsOverviewChart data={query.data} title="Transactions Overview" className="mb-10" />
        }}
      </OnQuerySuccess>
      <OnQuerySuccess query={settingsQuery}>
        {(query) => {
          const proxyData = query.data.proxy as ProxyData
          const endpointsNames = proxyData.endpoints?.map((endpoint: { name: string }) => endpoint.name)
          return (
            <div className="grid grid-cols-2 gap-4">
              {endpointsNames &&
                endpointsNames?.length > 1 &&
                endpointsNames.map((endpoint: string, index: number) => (
                  <TransactionsOverview key={index} endpoint={endpoint} title={endpoint} className="border p-2" />
                ))}
            </div>
          )
        }}
      </OnQuerySuccess>
    </Page>
  )
}
