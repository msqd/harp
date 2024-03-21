import { ArrowLeftCircleIcon } from "@heroicons/react/24/outline"
import { QueryObserverSuccessResult } from "react-query/types/core/types"
import { useNavigate, useParams } from "react-router-dom"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { Transaction } from "Models/Transaction"
import { Button } from "mkui/Components/Button"
import { H1 } from "mkui/Components/Typography"

import { TransactionDetail } from "./Containers/Detail"

function TransactionDetailPageOnQuerySuccess({ query }: { query: QueryObserverSuccessResult<Transaction> }) {
  const navigate = useNavigate()

  return (
    <>
      <div className="flex items-start">
        <Button variant="secondary" onClick={() => navigate(-1)}>
          <ArrowLeftCircleIcon className="h-4 inline-block mr-1 align-text-bottom" />
          Back
        </Button>
        <H1 className="ml-3">
          Transaction <span className="font-light">({query.data.id})</span>
        </H1>
      </div>
      <TransactionDetail transaction={query.data} />
    </>
  )
}

export function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const query = useTransactionsDetailQuery(id)

  return (
    <Page>
      <OnQuerySuccess query={query}>{(query) => <TransactionDetailPageOnQuerySuccess query={query} />}</OnQuerySuccess>
    </Page>
  )
}
