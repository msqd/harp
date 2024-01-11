import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useOverviewDataQuery } from "Domain/Overview"

import { TransactionsOverviewChart } from "./Components/OverviewChart"

interface TransactionsOverviewProps {
  endpoint?: string
  title?: string
  className?: string
  timeRange?: string
}

export const TransactionsOverview = ({ endpoint, title, className, timeRange }: TransactionsOverviewProps) => {
  const query = useOverviewDataQuery(endpoint, timeRange)

  return (
    <OnQuerySuccess query={query} queries={[query, query]}>
      {(query) => {
        return <TransactionsOverviewChart data={query.data} title={title} className={className} />
      }}
    </OnQuerySuccess>
  )
}
