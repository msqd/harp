import { StarIcon } from "@heroicons/react/24/outline"
import { formatDistance, formatDuration } from "date-fns"
import { useNavigate } from "react-router-dom"

import { PerformanceRatingBadge } from "Components/Badges"
import { useTransactionFlagCreateMutation } from "Domain/Transactions"
import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { Transaction } from "Models/Transaction"
import { DataTable } from "mkui/Components/DataTable"

import { RequestHeading, ResponseHeading } from "../Elements"

interface TransactionsDataTableProps {
  transactions: Transaction[]
}

export function TransactionDataTable({ transactions }: TransactionsDataTableProps) {
  const navigate = useNavigate()
  const createFlag = useTransactionFlagCreateMutation()

  const onStarClick = (event: React.MouseEvent, row: Transaction) => {
    event.stopPropagation()
    console.log("transaction", row)
    createFlag.mutate({ transactionId: row.id, flag: "favorite" })
  }
  const transactionColumnTypes = {
    favoriteAction: {
      label: "",
      get: (row: Transaction) => row,
      format: (row: Transaction) => (
        <StarIcon
          className="size-5 text-gray-300 hover:text-yellow-500"
          aria-hidden="true"
          onClick={(e) => onStarClick(e, row)}
        />
      ),
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
      get: (row: Transaction) => (row.elapsed ? Math.trunc(row.elapsed) / 1000 : null),
      format: (x: number) => {
        return (
          <div>
            <PerformanceRatingBadge duration={x} /> {formatDuration({ seconds: x })}{" "}
          </div>
        )
      },
    },
  }
  return (
    <>
      <DataTable<Transaction, { method: string; url: string; statusCode: string; responseBodySize: number }>
        types={transactionColumnTypes}
        onRowClick={(row: Transaction) => navigate(`/transactions/${row.id}`)}
        rows={transactions}
        columns={["favoriteAction", "request", "response", "elapsed", "started_at"]}
      />
    </>
  )
}
