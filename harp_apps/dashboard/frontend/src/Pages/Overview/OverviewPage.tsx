import { useState } from "react"
import tw, { styled } from "twin.macro"

import { Page, PageTitle } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSummaryDataQuery } from "Domain/Overview/useSummaryDataQuery.tsx"
import { useSystemSettingsQuery } from "Domain/System"
import { ButtonGroup } from "ui/Components/ButtonGroup"
import { Pane } from "ui/Components/Pane"
import { H2 } from "ui/Components/Typography"

import { PerformancesSummary } from "./Components/PerformancesSummary.tsx"
import { RateSummary } from "./Components/RateSummary.tsx"
import { TransactionsOverview } from "./Containers"
import { mapGetValues } from "./utils.ts"

export const OverviewPage = () => {
  const settingsQuery = useSystemSettingsQuery()

  const summaryQuery = useSummaryDataQuery()

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

  const StyledSummaryPane = styled(Pane)(() => [tw`overflow-hidden h-32 xl:h-40 2xl:h-48 relative`])

  return (
    <Page title={<PageTitle title="Overview" />}>
      <div className="grid grid-cols-3 gap-4">
        <StyledSummaryPane>
          <H2>Performances</H2>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => <PerformancesSummary mean={query.data.apdex.mean} data={mapGetValues(query.data.apdex.data)} />}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <H2>Transactions</H2>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <RateSummary
                rate={query.data.transactions.rate}
                period={query.data.transactions.period}
                data={mapGetValues(query.data.transactions.data)}
                color="#ADD8E6"
                badgeClassName="ring-blue-200"
              />
            )}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <H2>Errors</H2>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <RateSummary
                rate={query.data.errors.rate}
                period={query.data.errors.period}
                data={mapGetValues(query.data.errors.data)}
                color="#e6b3ad"
                badgeClassName="ring-red-200"
              />
            )}
          </OnQuerySuccess>
        </StyledSummaryPane>
      </div>

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
                  <Pane key={index}>
                    <TransactionsOverview endpoint={endpoint} title={endpoint} timeRange={timeRange} />
                  </Pane>
                ))}
            </div>
          )
        }}
      </OnQuerySuccess>
    </Page>
  )
}
