import { format } from "date-fns"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery"
import { Transaction } from "Models/Transaction"
import { SettingsTable } from "Pages/System/Components"
import { ucfirst } from "Utils/Strings"
import { Pane } from "ui/Components/Pane"

import { Duration } from "./Components/Duration.tsx"
import { Foldable } from "./Components/Foldable"
import { MessageBody } from "./Components/MessageBody"
import { MessageHeaders } from "./Components/MessageHeaders"
import { MessageSummary } from "./Components/MessageSummary"

import { CopyToClipboardWrapper } from "ui/Components/CopyToClipboardWrapper/CopyToClipboardWrapper"
function Tags({ tags }: { tags: [string, string] }) {
  return (
    <div className="flex gap-x-1">
      {tags.map(([tag, value]) => (
        <span key={tag} className="text-xs text-gray-500">
          {tag}={value}
        </span>
      ))}
    </div>
  )
}

export function TransactionDetailOnQuerySuccess({ query }: { query: QueryObserverSuccessResult<Transaction> }) {
  const transaction = query.data
  const [duration, apdex, cached, noCache] = [
    transaction.elapsed ? Math.trunc(transaction.elapsed) / 1000 : null,
    transaction.apdex ?? null,
    !!transaction.extras?.cached,
    !!transaction.extras?.no_cache,
  ]
  const tags = (transaction.tags ? Object.entries(transaction.tags) : []) as unknown as [string, string]
  return (
    <Pane hasDefaultPadding={false} className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm">
      <Foldable
        title={
          <div className="flex gap-x-0.5 items-center">
            <span className="grow">Transaction</span>
            <Duration
              duration={duration}
              apdex={apdex}
              cached={cached}
              noCache={noCache}
              verbose
              className="pl-1 pr-2"
            />
          </div>
        }
        children={tags.length ? <Tags tags={tags} /> : null}
      />
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
          <CopyToClipboardWrapper>
            <MessageHeaders id={message.headers} />
            <MessageBody id={message.body} />
          </CopyToClipboardWrapper>
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
