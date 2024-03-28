import { useState } from "react"
import { Sparklines, SparklinesCurve, SparklinesLine, SparklinesSpots } from "react-sparklines"
import tw, { styled } from "twin.macro"

import ApdexBadge from "Components/Badges/ApdexBadge.tsx"
import { StyledJumboBadge } from "Components/Badges/StyledJumboBadge.tsx"
import { Page, PageTitle } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"
import { ButtonGroup } from "ui/Components/ButtonGroup"
import { Pane } from "ui/Components/Pane"
import { H2 } from "ui/Components/Typography"

import { TransactionsOverview } from "./Containers"

import { useSummaryDataQuery } from "../../Domain/Overview/useSummaryDataQuery.tsx"

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
            {(query) => {
              return (
                <>
                  <div className="flex self-center relative z-10">
                    <ApdexBadge score={query.data.apdex.mean} size="xl" className="ring-1 ring-white" />
                  </div>
                  <Sparklines
                    min={0}
                    data={query.data.apdex.data.map((d: { value: number }) => d.value)}
                    style={{ margin: "-3px", position: "absolute", bottom: 0, left: 0, zIndex: 0 }}
                  >
                    <SparklinesCurve color="#ADD8E6" />
                    <SparklinesSpots />
                  </Sparklines>
                </>
              )
            }}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <H2>Transactions</H2>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => {
              return (
                <>
                  <div className="flex self-center relative z-10">
                    <StyledJumboBadge className="bg-white ring-1 ring-blue-200" size="xl" color="black">
                      {query.data.transactions.rate}{" "}
                      <span className="font-light">/{query.data.transactions.period}</span>
                    </StyledJumboBadge>
                  </div>
                  <Sparklines
                    min={0}
                    data={query.data.transactions.data.map((d: { value: number }) => d.value)}
                    style={{ margin: "-3px", position: "absolute", bottom: 0, left: 0 }}
                  >
                    <SparklinesLine color="#ADD8E6" />
                    <SparklinesSpots />
                  </Sparklines>
                </>
              )
            }}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <H2>Errors</H2>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => {
              return (
                <>
                  <div className="flex self-center relative z-10">
                    <StyledJumboBadge className="bg-white ring-1 ring-red-200" size="xl" color="black">
                      {query.data.errors.rate} <span className="font-light">/{query.data.errors.period}</span>
                    </StyledJumboBadge>
                  </div>
                  <Sparklines
                    min={0}
                    data={query.data.errors.data.map((d: { value: number }) => d.value)}
                    style={{ margin: "-3px", position: "absolute", bottom: 0, left: 0 }}
                  >
                    <SparklinesLine color="#e6b3ad" />
                    <SparklinesSpots />
                  </Sparklines>
                </>
              )
            }}
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
