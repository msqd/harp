import { useParams } from "react-router-dom"

import { Page, PageTitle } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useTransactionsDetailQuery } from "Domain/Transactions"

import { TransactionDetailOnQuerySuccess } from "./TransactionDetailOnQuerySuccess.tsx"

export function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const query = useTransactionsDetailQuery(id)

  return (
    <Page title={<PageTitle title="Transaction details" />}>
      <OnQuerySuccess query={query}>{(query) => <TransactionDetailOnQuerySuccess query={query} />}</OnQuerySuccess>
    </Page>
  )
}
