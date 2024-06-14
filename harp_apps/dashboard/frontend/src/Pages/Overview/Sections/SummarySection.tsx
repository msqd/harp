import { ArrowTopRightOnSquareIcon } from "@heroicons/react/24/outline"
import { Link } from "react-router-dom"
import tw, { styled } from "twin.macro"

import ApdexBadge from "Components/Badges/ApdexBadge.tsx"
import { StyledJumboBadge } from "Components/Badges/StyledJumboBadge.tsx"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSummaryDataQuery } from "Domain/Overview/useSummaryDataQuery.tsx"
import { Pane } from "ui/Components/Pane"
import { H2, H3 } from "ui/Components/Typography"
import { classNames } from "ui/Utilities"

import { SparklineChart } from "./Components/Charts/SparklineChart.tsx"

import { mapGetValues } from "../utils.ts"

const StyledSummaryPane = styled(Pane)(() => [tw`overflow-hidden h-32 xl:h-40 2xl:h-64 relative`])

function RateLegend({ rate, period, className }: { rate: number; period: string; className?: string }) {
  return (
    <div className="flex flex-col self-center relative z-10 items-start">
      <StyledJumboBadge className={classNames("bg-white ring-1", className)} size="xl" color="black">
        {rate} <span className="font-light">/{period}</span>
        <div className="text-xs font-normal text-gray-500 text-right">over the last 24 hours</div>
      </StyledJumboBadge>
    </div>
  )
}

export const SummarySection = () => {
  const summaryQuery = useSummaryDataQuery()
  return (
    <>
      <H2>Summary</H2>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StyledSummaryPane>
          <div className="flex items-start ">
            <H3>Performances (24h)</H3>
            <Link to="/transactions" className="leading-7 text-gray-400 mx-1 font-medium text-xs px-2">
              <ArrowTopRightOnSquareIcon className="h-3 w-3 inline-block" />
              details
            </Link>
          </div>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <SparklineChart data={mapGetValues(query.data.apdex.data)} color="#ADD8E6">
                <div className="flex self-center relative z-10">
                  <ApdexBadge score={query.data.apdex.mean} size="xl" className="ring-1 ring-white" />
                </div>
              </SparklineChart>
            )}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <div className="flex items-start ">
            <H3>Transactions (24h)</H3>
            <Link to="/transactions" className="leading-7 text-gray-400 mx-1 font-medium text-xs px-2">
              <ArrowTopRightOnSquareIcon className="h-3 w-3 inline-block" />
              details
            </Link>
          </div>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <SparklineChart data={mapGetValues(query.data.transactions.data)} color="#ADD8E6">
                <RateLegend
                  className="ring-blue-200"
                  rate={query.data.transactions.rate}
                  period={query.data.transactions.period}
                />
              </SparklineChart>
            )}
          </OnQuerySuccess>
        </StyledSummaryPane>
        <StyledSummaryPane>
          <div className="flex items-start ">
            <H3>Errors (24h)</H3>
            <Link
              to="/transactions?status=5xx&status=ERR"
              className="leading-7 text-gray-400 mx-1 font-medium text-xs px-2"
            >
              <ArrowTopRightOnSquareIcon className="h-3 w-3 inline-block" />
              details
            </Link>
          </div>
          <OnQuerySuccess query={summaryQuery}>
            {(query) => (
              <SparklineChart data={mapGetValues(query.data.errors.data)} color="#e6b3ad">
                <RateLegend className="ring-red-200" rate={query.data.errors.rate} period={query.data.errors.period} />
              </SparklineChart>
            )}
          </OnQuerySuccess>
        </StyledSummaryPane>
      </div>
    </>
  )
}
