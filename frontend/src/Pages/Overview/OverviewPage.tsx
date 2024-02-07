import { useState } from "react"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"
import { ButtonGroup } from "mkui/Components/ButtonGroup"
import { Pane } from "mkui/Components/Pane"

import { TransactionsOverview } from "./Containers/"

export const OverviewPage = () => {
  const settingsQuery = useSystemSettingsQuery()

  interface ProxyData {
    endpoints?: { name: string; port: number; url: string; description?: string }[]
  }
  const [timeRange, setTimeRange] = useState("7d")
  const setCurrentTimeRange = (timeRange: string) => {
    setTimeRange(timeRange)
  }

  const buttonProps = [
    { key: "1h", title: "1h" },
    { key: "24h", title: "24h" },
    { key: "7d", title: "7d" },
    { key: "1m", title: "1m" },
    { key: "1y", title: "1y" },
  ]

  return (
    <Page title="Overview" description="Useful insights">
      <div className="flex justify-end my-2">
        <ButtonGroup buttonProps={buttonProps} current={timeRange} setCurrent={setCurrentTimeRange} />
      </div>

      <Pane className="mb-4">
        <TransactionsOverview title="Transactions Overview" timeRange={timeRange} />
      </Pane>

      <OnQuerySuccess query={settingsQuery}>
        {(query) => {
          const proxyData = query.data.proxy as ProxyData
          const endpointsNames = proxyData.endpoints?.map((endpoint: { name: string }) => endpoint.name)
          return (
            <div className="grid grid-cols-2 gap-4">
              {endpointsNames &&
                endpointsNames?.length > 1 &&
                endpointsNames.map((endpoint: string, index: number) => (
                  <Pane>
                    <TransactionsOverview key={index} endpoint={endpoint} title={endpoint} timeRange={timeRange} />
                  </Pane>
                ))}
            </div>
          )
        }}
      </OnQuerySuccess>
    </Page>
  )
}
