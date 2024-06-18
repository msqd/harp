import { ArrowTopRightOnSquareIcon } from "@heroicons/react/24/outline"
import { Link } from "react-router-dom"
import tw, { css, styled } from "twin.macro"

import { StyledJumboBadge } from "Components/Badges/StyledJumboBadge.tsx"
import TpdexBadge from "Components/Badges/TpdexBadge.tsx"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSummaryDataQuery } from "Domain/Overview/useSummaryDataQuery.tsx"
import { Pane as BasePane } from "ui/Components/Pane"
import { H2, H3 } from "ui/Components/Typography"
import { classNames } from "ui/Utilities"

import { SummaryPerformancesChart, SummaryRateChart } from "./Components/LazyCharts"

const Pane = Object.assign(
  styled(BasePane)(() => [tw`overflow-hidden relative h-60`]),
  {
    /* Title of pane (eg: Performances 24h) */
    Title: styled.div(() => [tw`flex items-start`]),
    /* Link to details */
    Link: styled(Link)(() => [
      tw`leading-7 text-gray-400 mx-1 font-medium text-xs px-2 whitespace-nowrap z-10`,
      css`
        > svg {
          ${tw`h-3 w-3 inline-block`}
        }
      `,
    ]),
    /* Average badge (tpdex, rate...) */
    Badge: styled.div(() => [tw`inline-flex flex-col self-center relative z-10 items-start`]),
    /* Absolutely positionned chart */
    AbsoluteChart: styled.div(() => [tw`absolute w-full h-full left-0 top-0`]),
  },
)

function RateBadge({ rate, period, className }: { rate: number; period: string; className?: string }) {
  return (
    <Pane.Badge>
      <StyledJumboBadge className={classNames("bg-white ring-1", className)} size="xl" color="black">
        {rate} <span className="font-light">/{period}</span>
        <div className="text-xs font-normal text-gray-500 text-right">24h average</div>
      </StyledJumboBadge>
    </Pane.Badge>
  )
}

function SummaryPerformancesPane() {
  const query = useSummaryDataQuery()

  return (
    <Pane>
      <Pane.Title>
        <H3>Performances (24h)</H3>
        <Pane.Link to="/transactions">
          <ArrowTopRightOnSquareIcon />
          details
        </Pane.Link>
      </Pane.Title>

      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <>
              <Pane.Badge>
                <TpdexBadge score={query.data.tpdex.mean} size="xl" className="ring-1 ring-white">
                  <div className="text-xs font-normal text-right">24h average</div>
                </TpdexBadge>
              </Pane.Badge>

              <Pane.AbsoluteChart>
                <SummaryPerformancesChart data={query.data.tpdex.data} />
              </Pane.AbsoluteChart>
            </>
          )
        }}
      </OnQuerySuccess>
    </Pane>
  )
}

function SummaryTransactionsPane() {
  const query = useSummaryDataQuery()

  return (
    <Pane>
      <Pane.Title>
        <H3>Transactions (24h)</H3>
        <Pane.Link to="/transactions">
          <ArrowTopRightOnSquareIcon />
          details
        </Pane.Link>
      </Pane.Title>
      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <>
              <RateBadge
                className="ring-blue-200"
                rate={query.data.transactions.rate}
                period={query.data.transactions.period}
              />

              <Pane.AbsoluteChart>
                <SummaryRateChart data={query.data.transactions.data} color="#ADD8E6" />
              </Pane.AbsoluteChart>
            </>
          )
        }}
      </OnQuerySuccess>
    </Pane>
  )
}

function SummaryErrorsPane() {
  const query = useSummaryDataQuery()
  return (
    <Pane>
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
      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <>
              <RateBadge className="ring-red-200" rate={query.data.errors.rate} period={query.data.errors.period} />
              <Pane.AbsoluteChart>
                <SummaryRateChart data={query.data.errors.data} color="#e6b3ad" />
              </Pane.AbsoluteChart>
            </>
          )
        }}
      </OnQuerySuccess>
    </Pane>
  )
}

export const SummarySection = () => {
  return (
    <>
      <H2>Summary</H2>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <SummaryPerformancesPane />
        <SummaryTransactionsPane />
        <SummaryErrorsPane />
      </div>
    </>
  )
}
