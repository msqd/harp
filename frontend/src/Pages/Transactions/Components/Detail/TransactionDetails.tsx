import { Dialog } from "@headlessui/react"
import { ArrowLeftIcon, ArrowRightIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/outline"

import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { useBlobQuery } from "Domain/Transactions/useBlobQuery.tsx"
import { Transaction } from "Models/Transaction"

import { RequestHeading, ResponseHeading } from "../Elements"
import { TransactionMessagePanel } from "../List"

export function TransactionDetails({ transaction }: { transaction: Transaction }) {
  const { request } = getRequestFromTransactionMessages(transaction)
  const response = getResponseFromTransactionMessages(transaction)
  const requestHeadersQuery = useBlobQuery(request?.headers)
  const responseHeadersQuery = useBlobQuery(response?.headers)
  const requestBodyQuery = useBlobQuery(request?.body)
  const responseBodyQuery = useBlobQuery(response?.body)
  return (
    <div className="sm:flex sm:items-start ">
      <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
        <ArrowsRightLeftIcon className="h-6 w-6 text-blue-600" aria-hidden="true" />
      </div>
      <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full pr-12">
        <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-gray-900">
          Transaction <span className="font-light">({transaction.id})</span>
        </Dialog.Title>
        <div className="mt-2 text-sm text-gray-500 max-w-full">
          <div className="flex flex-row max-w-full">
            {request ? (
              <TransactionMessagePanel
                Icon={ArrowRightIcon}
                title={<RequestHeading as="h4" {...request} />}
                messageId={String(request.id)}
                headers={requestHeadersQuery.isSuccess ? requestHeadersQuery.data : null}
                body={requestBodyQuery.isSuccess ? requestBodyQuery.data : null}
              />
            ) : null}
            {response ? (
              <TransactionMessagePanel
                Icon={ArrowLeftIcon}
                title={<ResponseHeading as="h4" {...response} />}
                messageId={String(response.id)}
                headers={responseHeadersQuery.isSuccess ? responseHeadersQuery.data : null}
                body={responseBodyQuery.isSuccess ? responseBodyQuery.data : null}
              />
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
