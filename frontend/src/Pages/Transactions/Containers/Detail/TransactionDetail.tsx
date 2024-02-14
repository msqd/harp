import { ArrowLeftIcon, ArrowRightIcon, CommandLineIcon } from "@heroicons/react/24/outline"

import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery.ts"
import { getRequestFromTransactionMessages, getResponseFromTransactionMessages } from "Domain/Transactions/Utils"
import { useBlobQuery } from "Domain/Transactions/useBlobQuery.tsx"
import { Transaction } from "Models/Transaction"
import { SettingsTable } from "Pages/System/Components"
import { Tab } from "mkui/Components/Tabs"
import { H2 } from "mkui/Components/Typography"

import { RequestHeading, ResponseHeading } from "../../Components/Elements"
import { TransactionMessagePanel } from "../../Components/List"

export function TransactionDetail({ transaction }: { transaction: Transaction }) {
  const { request, endpoint: requestEndpoint } = getRequestFromTransactionMessages(transaction)
  const { response } = getResponseFromTransactionMessages(transaction)
  const requestHeadersQuery = useBlobQuery(request?.headers)
  const responseHeadersQuery = useBlobQuery(response?.headers)
  const requestBodyQuery = useBlobQuery(request?.body)
  const responseBodyQuery = useBlobQuery(response?.body)

  return (
    <Tab.Group>
      <Tab.List as="nav" aria-label="Tabs">
        {/*
        <Tab>
          <EyeIcon className="h-4 inline-block mr-1 align-text-bottom" />
          Overview
        </Tab>
        */}
        <Tab>
          <ArrowRightIcon className="h-4 inline-block mr-1 align-text-bottom" />
          Request
        </Tab>
        <Tab>
          <ArrowLeftIcon className="h-4 inline-block mr-1 align-text-bottom" />
          Response
        </Tab>
        <Tab>
          <CommandLineIcon className="h-4 inline-block mr-1 align-text-bottom" />
          Raw
        </Tab>
      </Tab.List>
      <Tab.Panels>
        <Tab.Panel>
          {request ? (
            <>
              <H2>
                Request
                <RequestHeading as="span" request={request} endpoint={requestEndpoint} className="inline-flex ml-4" />
              </H2>
              <TransactionMessagePanel
                messageId={String(request.id)}
                headers={
                  requestHeadersQuery.isSuccess && requestHeadersQuery.data ? requestHeadersQuery.data.content : null
                }
                body={requestBodyQuery.isSuccess && requestBodyQuery.data ? requestBodyQuery.data.content : null}
                contentType={
                  requestBodyQuery.isSuccess && requestBodyQuery.data ? requestBodyQuery.data.contentType : null
                }
              />
            </>
          ) : null}
        </Tab.Panel>
        <Tab.Panel className="max-w-full">
          {response ? (
            <>
              <H2>
                Response
                <ResponseHeading as="span" response={response} className="inline-flex ml-4" />
              </H2>
              <TransactionMessagePanel
                messageId={String(response.id)}
                headers={
                  responseHeadersQuery.isSuccess && responseHeadersQuery.data ? responseHeadersQuery.data.content : null
                }
                body={responseBodyQuery.isSuccess && responseBodyQuery.data ? responseBodyQuery.data.content : null}
                contentType={
                  responseBodyQuery.isSuccess && responseBodyQuery.data ? responseBodyQuery.data.contentType : null
                }
              />
            </>
          ) : null}
        </Tab.Panel>
        <Tab.Panel>
          <SettingsTable settings={transaction as KeyValueSettings} />
        </Tab.Panel>
      </Tab.Panels>
    </Tab.Group>
  )
}
