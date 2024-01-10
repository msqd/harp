import { useParams } from "react-router-dom"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { H1 } from "mkui/Components/Typography"

import { TransactionDetail } from "./Components/Detail"

export function TransactionsDetailPage() {
  const { id } = useParams<{ id: string }>()
  const query = useTransactionsDetailQuery(id)

  return (
    <Page>
      <OnQuerySuccess query={query}>
        {(query) => (
          <>
            <H1>
              Transaction <span className="font-light">({query.data.id})</span>
            </H1>
            <TransactionDetail transaction={query.data} />
          </>
        )}
      </OnQuerySuccess>
    </Page>
  )
}
