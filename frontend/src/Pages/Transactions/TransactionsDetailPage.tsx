import { ArrowLeftCircleIcon } from "@heroicons/react/24/outline"
import { useNavigate, useParams } from "react-router-dom"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { Button } from "mkui/Components/Button"
import { H1 } from "mkui/Components/Typography"

import { TransactionDetail } from "./Components/Detail"

export function TransactionsDetailPage() {
  const { id } = useParams<{ id: string }>()
  const query = useTransactionsDetailQuery(id)
  const navigate = useNavigate()

  return (
    <Page>
      <OnQuerySuccess query={query}>
        {(query) => (
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
        )}
      </OnQuerySuccess>
    </Page>
  )
}
