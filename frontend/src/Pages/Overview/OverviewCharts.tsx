import { PerformanceRatingBadge } from "Components/Badges"
import { useDashboardDataQuery } from "Domain/Dashboard"
import { DahsboardData } from "Models/Dashboard"
import { H2 } from "mkui/Components/Typography"

import { TransactionsChart } from "./TransactionsChart"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"

interface TransactionOverviewChartProps {
  data: DahsboardData
  title?: string
  className?: string
}
export const TransactionsOverviewChart = ({ data, title, className }: TransactionOverviewChartProps) => {
  return (
    <div className={className}>
      <H2>{title}</H2>
      <div style={{ display: "flex", alignItems: "center" }}>
        <div className="flex flex-col items-center">
          <div className="flex self-center text-3xl">
            <PerformanceRatingBadge duration={data.transactions.meanDuration} />
          </div>
          <div className="grid grid-cols-2 text-xs text-left align-text-bottom items-center self-center ml-10 mt-10">
            <span className="font-bold">Mean duration:</span>
            <span>{data.transactions.meanDuration}</span>
            <span className="font-bold">Errors:</span>
            <span>{data.errors.rate}%</span>
          </div>
        </div>
        <TransactionsChart data={data.dailyStats} width="90%"></TransactionsChart>
      </div>
    </div>
  )
}

interface TransactionsOverviewProps {
  endpoint?: string
  title?: string
  className?: string
}

export const TransactionsOverview = ({ endpoint, title, className }: TransactionsOverviewProps) => {
  const query = useDashboardDataQuery(endpoint)

  return (
    <OnQuerySuccess query={query} queries={[query, query]}>
      {(query) => {
        return <TransactionsOverviewChart data={query.data} title={title} className={className} />
      }}
    </OnQuerySuccess>
  )
}
