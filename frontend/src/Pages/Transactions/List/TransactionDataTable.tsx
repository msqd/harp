import { useState } from "react"
import { DataTable } from "mkui/Components/DataTable"
import { formatTransactionShortId, getDurationRatingBadge, ResponseStatusBadge } from "./formatters.tsx"
import { TransactionDetailsDialog } from "./TransactionDetailsDialog.tsx"
import { formatDistance, formatDuration } from "date-fns"
import { ArrowLeftIcon } from "@heroicons/react/24/outline"
import { RequestHeading } from "./RequestHeading.tsx"
import { Message, Transaction } from "Models/Transaction"

interface TransactionsDataTableProps {
  transactions: Transaction[]
}

const getRequestFromTransactionMessages = (transaction: Transaction) => {
  return transaction.messages?.find((message: Message) => message.kind === "request")
}

const getResponseFromTransactionMessages = (transaction: Transaction) => {
  return transaction.messages?.find((message: Message) => message.kind === "response")
}

const transactionColumnTypes = {
  id: {
    label: "Transaction",
    format: formatTransactionShortId,
    headerClassName: "w-1",
  },
  request: {
    label: "Request",
    get: (row: Transaction) => getRequestFromTransactionMessages(row) ?? null,
    format: RequestHeading,
  },
  response: {
    label: "Response",
    get: (row: Transaction) => getResponseFromTransactionMessages(row) ?? null,
    format: ({ id, statusCode }: { id: string; statusCode: number }) => (
      <div className="flex items-center" title={id}>
        <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
          <ArrowLeftIcon className="h-3 w-3 text-gray-500" aria-hidden="true" />
        </span>
        <ResponseStatusBadge statusCode={statusCode} />
        <span>...kB</span>
      </div>
    ),
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
        columns={["request", "response", "elapsed", "started_at"]}
      />
      <TransactionDetailsDialog current={current} setCurrent={setCurrent} />
    </>
  )
}
