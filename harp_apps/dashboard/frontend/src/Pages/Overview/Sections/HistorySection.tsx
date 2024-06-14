import { useState } from "react"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemSettingsQuery } from "Domain/System"
import { ButtonGroup } from "ui/Components/ButtonGroup"
import { Pane } from "ui/Components/Pane"
import { H2 } from "ui/Components/Typography"

import { TransactionsHistory } from "./Components/TransactionsHistory.tsx"

const buttonProps = [
  { key: "1h", title: "1h" },
  { key: "24h", title: "24h" },
  { key: "7d", title: "7d" },
  { key: "1m", title: "1m" },
  { key: "1y", title: "1y" },
]

interface ProxyData {
  endpoints?: { name: string; port: number; url: string; description?: string }[]
}

export const HistorySection = () => {
  const settingsQuery = useSystemSettingsQuery()

  const [timeRange, setTimeRange] = useState("7d")
  const setCurrentTimeRange = (timeRange: string) => {
    setTimeRange(timeRange)
  }
  return (
    <>
      <div className="flex justify-end my-2">
        <H2 className="grow">History</H2>
        <ButtonGroup buttonProps={buttonProps} current={timeRange} setCurrent={setCurrentTimeRange} />
      </div>

      <Pane className="mb-4">
        <TransactionsHistory title="Transactions" timeRange={timeRange} />
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
                  <Pane key={index}>
                    <TransactionsHistory endpoint={endpoint} title={endpoint} timeRange={timeRange} />
                  </Pane>
                ))}
            </div>
          )
        }}
      </OnQuerySuccess>
    </>
  )
}
