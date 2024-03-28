import { format } from "date-fns"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery.ts"
import { Transaction } from "Models/Transaction"
import { ucfirst } from "Utils/Strings.ts"
import { Pane } from "ui/Components/Pane"

import { Foldable } from "./Components/Foldable.tsx"
import { MessageBody } from "./Components/MessageBody.tsx"
import { MessageHeaders } from "./Components/MessageHeaders.tsx"
import { MessageSummary } from "./Components/MessageSummary.tsx"

import { SettingsTable } from "../System/Components/index.ts"

export function TransactionDetailOnQuerySuccess({ query }: { query: QueryObserverSuccessResult<Transaction> }) {
  return (
    <Pane hasDefaultPadding={false} className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm">
      {(query.data.messages || []).map((message) => (
        <Foldable
          title={
            <>
              <span className="mr-2">{ucfirst(message.kind)}</span>
              <MessageSummary kind={message.kind} summary={message.summary} endpoint={query.data.endpoint} />
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
      <Foldable title="Raw" open={false}>
        <SettingsTable settings={query.data as KeyValueSettings} />
      </Foldable>
    </Pane>
  )
}
