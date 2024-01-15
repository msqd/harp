import { StarIcon } from "@heroicons/react/24/outline"
import { formatDistance, formatDuration } from "date-fns"
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"

import { PerformanceRatingBadge } from "Components/Badges"
import { useTransactionFlagCreateMutation, useTransactionFlagDeleteMutation } from "Domain/Transactions"
import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { Transaction } from "Models/Transaction"
import { DataTable } from "mkui/Components/DataTable"

import { RequestHeading, ResponseHeading } from "../Elements"

interface TransactionsDataTableProps {
  transactions: Transaction[]
}

interface Row {
  transactionId: string
  flags: number[]
}

const FavoriteStar = ({ row }: { row: Row }) => {
  const flag = row.flags[0]
  const createFlag = useTransactionFlagCreateMutation()
  const deleteFlag = useTransactionFlagDeleteMutation()
  const [isFavorite, setIsFavorite] = useState(!!flag)

  const onStarClick = (event: React.MouseEvent, row: Row) => {
    event.stopPropagation()
    if (isFavorite) {
      deleteFlag.mutate({ flagId: flag })
      setIsFavorite(false)
      return
    } else {
      createFlag.mutate({ transactionId: row.transactionId, flag: 1 })
      setIsFavorite(true)
    }
  }

  useEffect(() => {
    setIsFavorite(!!flag)
  }, [row, flag])

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
    get: (row: Transaction) => ({
      transactionId: row.id,
      flags: row.extras?.flags ?? [],
    }),
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
