import { useState } from "react"
import { Transaction } from "Domain/Transactions/Types"
import { DataTable } from "mkui/Components/DataTable"
import {
  formatRequestMethod,
  formatRequestShortId,
  formatResponseShortId,
  formatStatusCode,
  formatTransactionShortId,
} from "./formatters.tsx"
import { isUrl } from "../../../Utils/Strings.ts"
import urlJoin from "url-join"
import { TransactionDetailsDialog } from "./TransactionDetailsDialog.tsx"

interface TransactionsDataTableProps {
  transactions: Transaction[]
  availableColumns?: any
  columns?: string[]
  formatters?: Record<string, (x: any) => string>
}

export function TransactionDataTable({ transactions }: TransactionsDataTableProps) {
  const [current, setCurrent] = useState<Transaction | null>(null)

  return (
    <>
      <DataTable<Transaction, { method: string; url: string; statusCode: string }>
        types={{
          id: {
            label: "Transaction",
            format: formatTransactionShortId,
            onClick: (row: Transaction) => setCurrent(row),
            headerClassName: "w-1",
          },
          request: {
            label: "Request",
            get: (row: Transaction) => row.request?.id || "-",
            format: formatRequestShortId,
            headerClassName: "w-1",
          },
          method: {
            label: "Method",
            get: (row: Transaction) => row.request?.method || "-",
            format: formatRequestMethod,
            headerClassName: "w-1",
          },
          url: {
            label: "URL",
            get: (row: Transaction): [string, string] => [row.endpoint || "-", row.request?.url || "-"],
            format: ([endpoint, url]: [string, string]) => (
              <>
                {isUrl(endpoint || "") ? (
                  urlJoin(endpoint || "?", "")
                ) : (
                  <span className="inline-flex items-center bg-gray-50 px-1 mx-1 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
                    {endpoint}
                  </span>
                )}
                {urlJoin("/", url || "")}
              </>
            ),
            headerClassName: "w-1",
          },
          response: {
            label: "Response",
            get: (row) => (row as Transaction).response?.id || "-",
            format: formatResponseShortId,
          },
          createdAt: {
            label: "Timestamp",
            format: (x) => new Date(x as string).toLocaleString(),
            className: "whitespace-nowrap",
          },
          statusCode: {
            label: "Status Code",
            get: (row: Transaction) => row.response?.statusCode || "-",
            format: formatStatusCode,
          },
        }}
        rows={transactions}
        columns={["id", "request", "method", "url", "response", "statusCode", "createdAt"]}
      />
      <TransactionDetailsDialog current={current} setCurrent={setCurrent} />
    </>
  )
}
