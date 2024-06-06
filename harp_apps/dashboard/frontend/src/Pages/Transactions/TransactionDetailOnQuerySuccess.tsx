import { CircleStackIcon } from "@heroicons/react/24/outline"
import { format, formatDuration } from "date-fns"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery"
import { Transaction } from "Models/Transaction"
import { SettingsTable } from "Pages/System/Components"
import { ucfirst } from "Utils/Strings"
import { Pane } from "ui/Components/Pane"

import { Foldable } from "./Components/Foldable"
import { MessageBody } from "./Components/MessageBody"
import { MessageHeaders } from "./Components/MessageHeaders"
import { MessageSummary } from "./Components/MessageSummary"

import ApdexBadge from "../../Components/Badges/ApdexBadge.tsx"

export function TransactionDetailOnQuerySuccess({ query }: { query: QueryObserverSuccessResult<Transaction> }) {
  const transaction = query.data
  const [duration, apdex, cached] = [
    transaction.elapsed ? Math.trunc(transaction.elapsed) / 1000 : null,
    transaction.apdex,
    !!transaction.extras?.cached,
  ]
  return (
    <Pane hasDefaultPadding={false} className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm">
      <Foldable
        title={
          <div className="flex gap-x-0.5 items-center">
            <span className="grow">Transaction</span>
            {duration !== null ? (
              <>
                {apdex !== null ? <ApdexBadge score={apdex} /> : null}
                <span className="font-normal">{formatDuration({ seconds: duration })}</span>
                {cached ? (
                  <span className="flex items-center font-normal text-gray-400">
                    <CircleStackIcon className="w-4 text-xs inline" title="From proxy cache" />
                    <span>(cached)</span>
                  </span>
                ) : null}
              </>
            ) : null}
          </div>
        }
      ></Foldable>
      {(transaction.messages || []).map((message) => (
        <Foldable
          key={message.id}
          title={
            <>
              <span className="mr-2">{ucfirst(message.kind)}</span>
              <MessageSummary kind={message.kind} summary={message.summary} endpoint={transaction.endpoint} />
            </>
          }
          subtitle={
            message.created_at ? (
              <span className="text-xs text-gray-500">{format(new Date(message.created_at), "PPPPpppp")}</span>
            ) : undefined
          }
          open={message.kind != "error"}
        >
          <MessageHeaders id={message.headers} />
          <MessageBody id={message.body} />
        </Foldable>
      ))}
      {import.meta.env.DEV ? (
        <Foldable title="Raw" open={false}>
          <SettingsTable settings={transaction as KeyValueSettings} />
        </Foldable>
      ) : null}
    </Pane>
  )
}
