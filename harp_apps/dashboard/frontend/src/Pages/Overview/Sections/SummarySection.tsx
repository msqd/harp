import tw, { styled } from "twin.macro"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSummaryDataQuery } from "Domain/Overview/useSummaryDataQuery.tsx"
import { Pane } from "ui/Components/Pane"
import { H2, H3 } from "ui/Components/Typography"

import { PerformancesSparklineGraph } from "./Components/PerformancesSparklineGraph.tsx"
import { RateSparklineGraph } from "./Components/RateSparklineGraph.tsx"

import { mapGetValues } from "../utils.ts"

const StyledSummaryPane = styled(Pane)(() => [tw`overflow-hidden h-32 xl:h-40 2xl:h-48 relative`])

export const SummarySection = () => {
  const summaryQuery = useSummaryDataQuery()
  return (
    <>
      <H2>Summary</H2>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StyledSummaryPane>
          <H3>Performances (24h)</H3>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <PerformancesSparklineGraph mean={query.data.apdex.mean} data={mapGetValues(query.data.apdex.data)} />
            )}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <H3>Transactions (24h)</H3>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <RateSparklineGraph
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
          <H3>Errors (24h)</H3>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <RateSparklineGraph
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
    </>
  )
}
