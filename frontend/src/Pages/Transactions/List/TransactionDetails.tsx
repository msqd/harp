import { useRequestsDetailQuery, useResponsesDetailQuery } from "Domain/Transactions"
import { ArrowLeftIcon, ArrowRightIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/outline"
import { Dialog } from "@headlessui/react"
import { truncate } from "Utils/Strings.ts"
import { TransactionMessagePanel } from "./TransactionMessagePanel.tsx"
import { RequestHeading } from "./RequestHeading.tsx"
import { Transaction } from "Models/Transaction"

export function TransactionDetails({ transaction }: { transaction: Transaction }) {
  const requestsDetailQuery = useRequestsDetailQuery(transaction.request?.id)
  const responsesDetailQuery = useResponsesDetailQuery(transaction.response?.id)
  return (
    <div className="sm:flex sm:items-start ">
      <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
        <ArrowsRightLeftIcon className="h-6 w-6 text-blue-600" aria-hidden="true" />
      </div>
      <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full pr-12">
        <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-gray-900">
          Transaction ({truncate(transaction.id, 7)})
        </Dialog.Title>
        <div className="mt-2 text-sm text-gray-500 max-w-full">
          <div className="flex flex-row max-w-full">
            <TransactionMessagePanel
              Icon={ArrowRightIcon}
              title={
                <RequestHeading
                  as="h4"
                  id={transaction.request?.id || ""}
                  method={transaction.request?.method || ""}
                  endpoint={transaction.endpoint || ""}
                  url={transaction.request?.url || ""}
                />
              }
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
