import { CircleStackIcon, StarIcon } from "@heroicons/react/24/outline"
import { formatDistance, formatDuration } from "date-fns"
import { useState } from "react"

import ApdexBadge from "Components/Badges/ApdexBadge.tsx"
import { useSetUserFlagMutation } from "Domain/Transactions"
import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { Message, Transaction } from "Models/Transaction"
import { DataTable } from "ui/Components/DataTable"

import { MessageSummary } from "../MessageSummary.tsx"

interface TransactionsDataTableProps {
  transactions: Transaction[]
  onSelectionChange?: (selected: Transaction | null) => void
  selected?: Transaction
}

interface Row {
  transactionId: string
  flags: string[]
}

const SetUnsetFavoriteAction = ({ row }: { row: Row }) => {
  const setUserFlagMutation = useSetUserFlagMutation()
  const [isFavorite, setIsFavorite] = useState(row.flags.includes("favorite"))

  const onClick = (event: React.MouseEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setUserFlagMutation.mutate({ transactionId: row.transactionId, flag: "favorite", value: !isFavorite })
    setIsFavorite(!isFavorite)
    return false
  }

  return (
    <StarIcon
      className={isFavorite ? "size-5 fill-current text-yellow-500" : "size-5 text-gray-300 hover:text-yellow-500"}
      aria-hidden="true"
      onClick={onClick}
    />
  )
}

const transactionColumnTypes = {
  favoriteAction: {
    label: "",
    get: (row: Transaction) => ({
      transactionId: row.id,
      flags: row.extras?.flags ?? [],
    }),
    format: (row: Row) => <SetUnsetFavoriteAction key={row.transactionId} row={row} />,
    headerClassName: "w-1",
  },
  request: {
    label: "Request",
    get: (row: Transaction) => getRequestFromTransactionMessages(row),
    format: ({ request, endpoint }: { request?: Message; endpoint?: string }) =>
      request ? <MessageSummary kind={request.kind} summary={request.summary} endpoint={endpoint} /> : null,
    className: "truncate max-w-0 w-full",
  },
  response: {
    label: "Response",
    get: (row: Transaction) => getResponseFromTransactionMessages(row) ?? null,
    format: ({ response, error, endpoint }: { response?: Message; error?: Message; endpoint?: string }) => {
      if (error) {
        return <MessageSummary kind={error.kind} summary={error.summary} endpoint={endpoint} />
      }

      if (response) {
        return <MessageSummary kind={response.kind} summary={response.summary} endpoint={endpoint} />
      }

      return <MessageSummary />
    },
  },
  started_at: {
    label: "Date",
    format: (x: string) => {
      return <div title={x}>{formatDistance(new Date(x), new Date(), { addSuffix: true })}</div>
    },
  },
  elapsed: {
    label: "Duration",
    get: (row: Transaction) => [row.elapsed ? Math.trunc(row.elapsed) / 1000 : null, row.apdex, !!row.extras?.cached],
    format: ([duration, apdex, cached]: [number | null, number | null, boolean]) => {
      if (duration !== null) {
        return (
          <div className="flex gap-x-0.5 items-center">
            {apdex !== null ? <ApdexBadge score={apdex} /> : null}
            <span>{formatDuration({ seconds: duration })}</span>
            {cached ? <CircleStackIcon className="w-4 text-xs text-gray-400 inline" title="From proxy cache" /> : null}
          </div>
        )
      }
    },
  },
}

export function TransactionDataTable({ transactions, onSelectionChange, selected }: TransactionsDataTableProps) {
  return (
    <>
      <DataTable<Transaction, { method: string; url: string; statusCode: string; responseBodySize: number }>
        types={transactionColumnTypes}
        onRowClick={onSelectionChange}
        rows={transactions}
        columns={["favoriteAction", "request", "response", "elapsed", "started_at"]}
        selected={selected}
      />
    </>
  )
}
