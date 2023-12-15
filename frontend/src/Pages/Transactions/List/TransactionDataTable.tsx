import { useState } from "react"
import { DataTable } from "mkui/Components/DataTable"
import { formatTransactionShortId, getDurationRatingBadge } from "./Utilities/formatters.tsx"
import { TransactionDetailsDialog } from "./TransactionDetailsDialog.tsx"
import { formatDistance, formatDuration } from "date-fns"
import { ArrowsRightLeftIcon } from "@heroicons/react/24/outline"
import { RequestHeading } from "./Components/RequestHeading.tsx"
import { Transaction } from "Models/Transaction"
import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { ResponseHeading } from "./Components/ResponseHeading.tsx"

interface TransactionsDataTableProps {
  transactions: Transaction[]
}

const transactionColumnTypes = {
  id: {
    label: "Transaction",
    format: (id: string) => (
      <>
        <span className="mx-auto flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 float-left">
          <ArrowsRightLeftIcon className="h-3 w-3 text-blue-600" aria-hidden="true" />
        </span>
        {formatTransactionShortId(id)}
      </>
    ),
    headerClassName: "w-28",
  },
  request: {
    label: "Request",
    get: (row: Transaction) => getRequestFromTransactionMessages(row) ?? null,
    format: RequestHeading,
  },
  response: {
    label: "Response",
    get: (row: Transaction) => getResponseFromTransactionMessages(row) ?? null,
    format: ResponseHeading,
  },
  started_at: {
    label: "Date",
    format: (x: string) => {
      return <div title={x}>{formatDistance(new Date(x), new Date(), { addSuffix: true })}</div>
    },
  },
  elapsed: {
    label: "Duration",
    format: (x: number) => {
      return (
        <div>
          {getDurationRatingBadge(x)} {formatDuration({ seconds: x })}{" "}
        </div>
      )
    },
  },
}

export function TransactionDataTable({ transactions }: TransactionsDataTableProps) {
  const [current, setCurrent] = useState<Transaction | null>(null)

  return (
    <>
      {/*durationRatingScale.map((x) => getDurationRatingBadge(x.threshold || 10))*/}

      <DataTable<Transaction, { method: string; url: string; statusCode: string; responseBodySize: number }>
        types={transactionColumnTypes}
        onRowClick={(row: Transaction) => setCurrent(row)}
        rows={transactions}
        columns={["id", "request", "response", "elapsed", "started_at"]}
      />
      <TransactionDetailsDialog current={current} setCurrent={setCurrent} />
    </>
  )
}
