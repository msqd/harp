import { Link, useParams } from "react-router"

import { Page, PageTitle } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { TransactionNotFoundError } from "Domain/Transactions/useTransactionsDetailQuery.ts"
import { NotFound } from "ui/Components/NotFound"

import { TransactionDetailOnQuerySuccess } from "./TransactionDetailOnQuerySuccess.tsx"

function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const query = useTransactionsDetailQuery(id)
  const notFound = query.error instanceof TransactionNotFoundError

  return (
    <Page title={notFound ? undefined : <PageTitle title="Transaction details" />}>
      {notFound ? (
        <NotFound
          title="Transaction not found"
          action={
            <Link to="/transactions" className="text-sm font-semibold text-blue-600 hover:text-blue-500">
              Back to transactions
            </Link>
          }
        >
          This transaction does not exist or has been removed.
        </NotFound>
      ) : (
        <OnQuerySuccess query={query}>{(query) => <TransactionDetailOnQuerySuccess query={query} />}</OnQuerySuccess>
      )}
    </Page>
  )
}

export default TransactionDetailPage
