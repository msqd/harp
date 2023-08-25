import { Transaction, TransactionMessage } from "Domain/Transactions/Types"
import urlJoin from "url-join"
import { ComponentType, Dispatch, Fragment, SetStateAction, useState } from "react"
import { Dialog, Transition } from "@headlessui/react"
import { ArrowLeftIcon, ArrowRightIcon, ArrowsRightLeftIcon, XMarkIcon } from "@heroicons/react/24/outline"
import { useRequestsDetailQuery, useResponsesDetailQuery } from "Domain/Transactions"
import { DataTable } from "mkui/Components/DataTable"

interface TransactionsListProps {
  transactions: Transaction[]
}

interface TransactionsDataTableProps {
  transactions: Transaction[]
  availableColumns?: any
  columns?: string[]
  formatters?: Record<string, (x: any) => string>
}

function isUrl(urlOrWhatever: string) {
  let url

  try {
    url = new URL(urlOrWhatever)
  } catch (_) {
    return false
  }

  return url.protocol === "http:" || url.protocol === "https:"
}

function truncateString(str: string, num: number) {
  // If the length of str is less than or equal to num
  // just return str--don't truncate it.
  if (str.length <= num) {
    return str
  }
  // Return str truncated with '...' concatenated to the end of str.
  return str.slice(0, num) + "…"
}

function HeadersTable({ headers }: { headers: Record<string, string> }) {
  return (
    <table className="divide-y">
      <tbody className="divide-y divide-gray-200 bg-white">
        {Object.entries(headers).map(([k, v], index) => (
          <tr key={index}>
            <td className="whitespace-nowrap py-1 pl-4 pr-3 text-sm text-gray-500 sm:pl-0">{k}</td>
            <td className="whitespace-nowrap px-2 py-1 text-sm text-gray-900">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function TransactionMessagePanel({
  Icon,
  title,
  messageId,
  message,
}: {
  Icon: ComponentType<any>
  message: TransactionMessage | Record<string, never> | null
  messageId: string | null
  title: string
}) {
  return (
    <div className="flex-none w-1/2 overflow-none max-h-screen px-1">
      <h4 className="text-sm font-semibold leading-6 text-gray-900">
        <span className="mx-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 float-left">
          <Icon className="h-4 w-4 text-blue-600" aria-hidden="true" />
        </span>

        <span className="px-2 ">
          {title} <span className="text-gray-400">({truncateString(messageId || "-", 7)})</span>
        </span>
      </h4>
      <div className="w-full overflow-auto">
        {message == null ? (
          <div>Loading...</div>
        ) : (
          <>
            <HeadersTable headers={message.headers || {}} />
            <pre className="w-fit overflow-x-auto p-4 text-xs text-black">{message.content}</pre>
          </>
        )}
      </div>
    </div>
  )
}

function TransactionDetails({ transaction }: { transaction: Transaction }) {
  const requestsDetailQuery = useRequestsDetailQuery(transaction.request?.id)
  const responsesDetailQuery = useResponsesDetailQuery(transaction.response?.id)
  return (
    <div className="sm:flex sm:items-start ">
      <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
        <ArrowsRightLeftIcon className="h-6 w-6 text-blue-600" aria-hidden="true" />
      </div>
      <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full pr-12">
        <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-gray-900">
          Transaction ({truncateString(transaction.id, 7)})
        </Dialog.Title>
        <div className="mt-2 text-sm text-gray-500 max-w-full">
          <div className="flex flex-row max-w-full">
            <TransactionMessagePanel
              Icon={ArrowRightIcon}
              title={transaction.request ? transaction.request.method + " " + transaction.request.url : "-"}
              messageId={transaction.request?.id || null}
              message={requestsDetailQuery.isSuccess ? requestsDetailQuery.data : null}
            />
            <TransactionMessagePanel
              Icon={ArrowLeftIcon}
              title={transaction.response ? `HTTP ${transaction.response.statusCode}` : "-"}
              messageId={transaction.response?.id || null}
              message={responsesDetailQuery.isSuccess ? responsesDetailQuery.data : null}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function createShortIdFormatter({
  maxLength = 7,
  Icon = null,
}: { maxLength?: number; Icon?: ComponentType<any> | null } = {}) {
  return (id: unknown) => {
    return (
      <span className="font-mono inline-flex items-center bg-white px-1 mx-1 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
        {Icon ? (
          <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
            <Icon className="h-3 w-3 text-gray-500" aria-hidden="true" />
          </span>
        ) : null}
        {truncateString(id as string, maxLength)}
      </span>
    )
  }
}

const formatTransactionShortId = createShortIdFormatter({ Icon: ArrowsRightLeftIcon, maxLength: 10 })
const formatRequestShortId = createShortIdFormatter({ Icon: ArrowRightIcon })
const formatResponseShortId = createShortIdFormatter({ Icon: ArrowLeftIcon })
const formatRequestMethod = (method: unknown) => {
  switch (method) {
    case "GET":
      return (
        <span className="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
          {method}
        </span>
      )
  }
  return (
    <span className="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-700 ring-1 ring-inset ring-green-600/20">
      {method as string}
    </span>
  )
}

function TransactionDetailsDialog({
  current,
  setCurrent,
}: {
  current: Transaction | null
  setCurrent: Dispatch<SetStateAction<Transaction | null>>
}) {
  return (
    <Transition.Root show={current !== null} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={() => setCurrent(null)}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-100"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-100"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-100"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-fit sm:min-6/12 sm:max-w-90% sm:p-6 max-h-11/12">
                <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
                  <button
                    type="button"
                    className="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                    onClick={() => setCurrent(null)}
                  >
                    <span className="sr-only">Close</span>

                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                {current !== null ? <TransactionDetails transaction={current} /> : null}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}

function TransactionDataTable({ transactions }: TransactionsDataTableProps) {
  const [current, setCurrent] = useState<Transaction | null>(null)

  return (
    <>
      <DataTable<Transaction, { method: string; statusCode: string }>
        types={{
          id: {
            label: "Transaction",
            format: formatTransactionShortId,
            onClick: (row: Transaction) => setCurrent(row),
          },
          endpoint: {
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
          },
          request: {
            label: "Request",
            get: (row) => (row as Transaction).request?.id || "-",
            format: formatRequestShortId,
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
          method: {
            label: "Method",
            get: (row) => (row as Transaction).request?.method || "-",
            format: formatRequestMethod,
          },
          statusCode: { label: "Status Code" },
        }}
        rows={transactions}
        columns={["id", "method", "endpoint", "request", "response", "createdAt"]}
      />
      <TransactionDetailsDialog current={current} setCurrent={setCurrent} />
    </>
  )
}

function OldTransactionDataTable({ transactions }: TransactionsDataTableProps) {
  const [current, setCurrent] = useState<Transaction | null>(null)

  return (
    <>
      <table className="min-w-full divide-y divide-gray-300 text-left">
        <thead>
          <tr>
            <th
              scope="col"
              className="whitespace-nowrap py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-0 w-1"
            >
              ID
            </th>
            <th scope="col" className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1">
              Method
            </th>
            <th scope="col" className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1">
              URL
            </th>
            <th scope="col" className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1">
              Status Code
            </th>
            <th scope="col" className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900">
              Request
            </th>
            <th scope="col" className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900">
              Response
            </th>
            <th scope="col" className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1">
              Timestamp
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {/* TODO this should not be cast but we need it while we have this type specific code */}
          {transactions.map((transaction) => (
            <tr key={transaction.id} className={transaction == current ? "bg-blue-100" : ""}>
              <td className="whitespace-nowrap py-2 pl-4 pr-3 text-sm text-gray-500 sm:pl-0 font-mono">
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault()
                    setCurrent(transaction)
                    return false
                  }}
                >
                  <span title={transaction.id}>{truncateString(transaction.id, 3) + transaction.id.slice(-3)}</span>
                </a>
              </td>
              <td className="whitespace-nowrap px-2 py-2 text-sm font-medium text-gray-900">
                <span className="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                  {transaction.request?.method || "-"}
                </span>
              </td>
              <td className="whitespace-nowrap px-2 py-2 text-sm font-medium text-gray-900">
                {isUrl(transaction.endpoint || "") ? (
                  urlJoin(transaction.endpoint || "?", "")
                ) : (
                  <span className="inline-flex items-center bg-gray-50 px-1 mx-1 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
                    {transaction.endpoint}
                  </span>
                )}
                {urlJoin("/", transaction.request?.url || "")}
              </td>
              <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-900">
                {transaction.response?.statusCode ? (
                  <span className="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                    {/* vert bleu jaune ou rouge */}
                    {transaction.response.statusCode}
                  </span>
                ) : (
                  "-"
                )}
              </td>
              <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-500 font-mono">
                {truncateString(transaction.request?.id || "-", 7)}
              </td>
              <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-500 font-mono">
                {truncateString(transaction.response?.id || "-", 7)}
              </td>
              <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-900">
                {new Date(transaction.createdAt).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

export function TransactionsList({ transactions }: TransactionsListProps) {
  return (
    <div className="py-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-base font-semibold leading-6 text-gray-900">Transactions</h1>
          <p className="mt-2 text-sm text-gray-700">List of HTTP transactions</p>
        </div>
      </div>
      <div className="mt-8 flow-root">
        <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <TransactionDataTable<Transaction> transactions={transactions} />
          </div>
        </div>
      </div>
    </div>
  )
}
