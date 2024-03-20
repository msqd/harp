import { Transition } from "@headlessui/react"
import { XMarkIcon } from "@heroicons/react/24/outline"
import { Fragment, useState } from "react"

import { RequestHeading, ResponseHeading } from "./Components/Elements"
import { TransactionDetail } from "./Containers/Detail"

import { useTransactionsDetailQuery } from "../../Domain/Transactions"
import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "../../Domain/Transactions/Utils"

export function TransactionDetailPanel({ id }: { id: string }) {
  const [open, setOpen] = useState(true)
  const query = useTransactionsDetailQuery(id)

  return (
    <Transition.Root show={!!id && open} as={Fragment}>
      <div
        className="relative z-10"
        onClick={(e) => {
          // to avoid closing the panel when clicking inside it
          e.stopPropagation()
        }}
      >
        <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 sm:pl-16">
          <Transition.Child
            as={Fragment}
            enter="transform transition ease-in-out duration-200"
            enterFrom="translate-x-full"
            enterTo="translate-x-0"
            leave="transform transition ease-in-out duration-200"
            leaveFrom="translate-x-0"
            leaveTo="translate-x-full"
          >
            <div className="pointer-events-auto w-screen max-w-5xl">
              <div className="flex h-full flex-col overflow-y-scroll bg-white py-6 shadow-xl">
                <div className="px-4 sm:px-6">
                  <div className="flex items-start justify-between">
                    <h1 className="text-base font-semibold leading-6 text-gray-900">
                      {query.isSuccess
                        ? (() => {
                            const { request, endpoint: requestEndpoint } = getRequestFromTransactionMessages(query.data)
                            const { response } = getResponseFromTransactionMessages(query.data)
                            return (
                              <>
                                <RequestHeading
                                  as="span"
                                  request={request}
                                  endpoint={requestEndpoint}
                                  className="inline-flex ml-4"
                                />
                                {response ? (
                                  <ResponseHeading as="span" response={response} className="inline-flex ml-4" />
                                ) : (
                                  "..."
                                )}
                              </>
                            )
                          })()
                        : "..."}
                    </h1>
                    <div className="ml-3 flex h-7 items-center">
                      <button
                        type="button"
                        className="relative rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                        onClick={() => setOpen(false)}
                      >
                        <span className="absolute -inset-2.5" />
                        <span className="sr-only">Close panel</span>
                        <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                </div>
                <div className="relative mt-6 flex-1 px-4 sm:px-6">
                  {query.isSuccess ? <TransactionDetail transaction={query.data} /> : null}
                </div>
              </div>
            </div>
          </Transition.Child>
        </div>
      </div>
    </Transition.Root>
  )
}
