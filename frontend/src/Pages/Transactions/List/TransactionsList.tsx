import { Transaction } from "Domain/Transactions/Types"
import urlJoin from "url-join"
import { Fragment, useState } from "react"
import { Dialog, Transition } from "@headlessui/react"
import { ExclamationTriangleIcon, XMarkIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/outline"

interface TransactionsListProps {
  transactions: Transaction[]
}

interface DataTableProps<TRow> {
  transactions: TRow[]
  availableColumns?: any
  columns?: string[]
  formatters?: Record<string, (x: any) => string>
}

function isUrl(urlOrWhatever: string | any) {
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

function DataTable<TRow>({ transactions }: DataTableProps<TRow>) {
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
          {(transactions as Transaction[]).map((transaction) => (
            <tr key={transaction.id}>
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
      <Transition.Root show={current !== null} as={Fragment}>
        <Dialog as="div" className="relative z-10" onClose={() => setCurrent(null)}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
          </Transition.Child>

          <div className="fixed inset-0 z-10 overflow-y-auto">
            <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
              <Transition.Child
                as={Fragment}
                enter="ease-out duration-300"
                enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                enterTo="opacity-100 translate-y-0 sm:scale-100"
                leave="ease-in duration-200"
                leaveFrom="opacity-100 translate-y-0 sm:scale-100"
                leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              >
                <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-fit sm:min-6/12 sm:max-w-90 sm:p-6">
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
                  <div className="sm:flex sm:items-start">
                    <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                      <ArrowsRightLeftIcon className="h-6 w-6 text-blue-600" aria-hidden="true" />
                    </div>
                    {current !== null ? (
                      <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                        <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-gray-900">
                          Transaction details - {current.id}
                        </Dialog.Title>
                        <div className="mt-2">
                          <p className="text-sm text-gray-500">
                            <div>Request id: {current.request?.id}</div>
                            <div>Response id: {current.response?.id}</div>
                          </p>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition.Root>
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
            <DataTable<Transaction> transactions={transactions} />
          </div>
        </div>
      </div>
    </div>
  )
}
