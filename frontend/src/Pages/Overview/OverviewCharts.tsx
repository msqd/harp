import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useDashboardDataQuery } from "Domain/Overview"

import { TransactionsOverviewChart } from "./Components/OverviewChart"

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
