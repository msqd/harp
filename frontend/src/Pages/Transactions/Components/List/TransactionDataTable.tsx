import { StarIcon } from "@heroicons/react/24/outline"
import { formatDistance, formatDuration } from "date-fns"
import { useState } from "react"
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

interface Extras {
  flags: string[]
}

interface Row {
  id: string
  extras: Extras
}

const FavoriteStar = ({ row }: { row: Row }) => {
  const createFlag = useTransactionFlagCreateMutation()
  const [isFavorite, setIsFavorite] = useState(row.extras.flags.length > 0)

  const onStarClick = (event: React.MouseEvent, row: Row) => {
    event.stopPropagation()
    if (isFavorite) {
      console.log("transaction already fav")
      return
    } else {
      console.log("transaction", row)
      createFlag.mutate({ transactionId: row.id, flag: "favorite" })
      setIsFavorite(true)
    }
  }

  return (
    <StarIcon
      className={isFavorite ? "size-5 fill-current text-yellow-500" : "size-5 text-gray-300 hover:text-yellow-500"}
      aria-hidden="true"
      onClick={(e) => onStarClick(e, row)}
    />
  )
}

const transactionColumnTypes = {
  favoriteAction: {
    label: "",
    get: (row: Transaction) => row,
    format: (row: Row) => <FavoriteStar row={row} />,
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

export function TransactionDataTable({ transactions }: TransactionsDataTableProps) {
  const navigate = useNavigate()

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
