import { ArrowLeftIcon, ArrowRightIcon } from "@heroicons/react/24/outline"

import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { useBlobQuery } from "Domain/Transactions/useBlobQuery.tsx"
import { Transaction } from "Models/Transaction"
import { Tab } from "mkui/Components/Tabs"

import { RequestHeading, ResponseHeading } from "../Elements"
import { TransactionMessagePanel } from "../List"

export function TransactionDetail({ transaction }: { transaction: Transaction }) {
  const { request } = getRequestFromTransactionMessages(transaction)
  const response = getResponseFromTransactionMessages(transaction)
  const requestHeadersQuery = useBlobQuery(request?.headers)
  const responseHeadersQuery = useBlobQuery(response?.headers)
  const requestBodyQuery = useBlobQuery(request?.body)
  const responseBodyQuery = useBlobQuery(response?.body)

  return (
    <Tab.Group>
      <Tab.List as="nav" aria-label="Tabs">
        <Tab>Overview</Tab>
        <Tab>Request</Tab>
        <Tab>Response</Tab>
      </Tab.List>
      <Tab.Panels>
        <Tab.Panel>{JSON.stringify(transaction)}</Tab.Panel>
        <Tab.Panel>
          {request ? (
            <TransactionMessagePanel
              Icon={ArrowRightIcon}
              title={<RequestHeading as="h4" {...request} />}
              messageId={String(request.id)}
              headers={
                requestHeadersQuery.isSuccess && requestHeadersQuery.data ? requestHeadersQuery.data.content : null
              }
              body={requestBodyQuery.isSuccess && requestBodyQuery.data ? requestBodyQuery.data.content : null}
              contentType={
                requestBodyQuery.isSuccess && requestBodyQuery.data ? requestBodyQuery.data.contentType : null
              }
            />
          ) : null}
        </Tab.Panel>
        <Tab.Panel>
          {response ? (
            <TransactionMessagePanel
              Icon={ArrowLeftIcon}
              title={<ResponseHeading as="h4" {...response} />}
              messageId={String(response.id)}
              headers={
                responseHeadersQuery.isSuccess && responseHeadersQuery.data ? responseHeadersQuery.data.content : null
              }
              body={responseBodyQuery.isSuccess && responseBodyQuery.data ? responseBodyQuery.data.content : null}
              contentType={
                responseBodyQuery.isSuccess && responseBodyQuery.data ? responseBodyQuery.data.contentType : null
              }
            />
          ) : null}
        </Tab.Panel>
      </Tab.Panels>
    </Tab.Group>
  )
}
