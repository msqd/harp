import { ComponentType } from "react"
import { TransactionMessage } from "../../../Domain/Transactions/Types"
import { truncate } from "../../../Utils/Strings.ts"
import { HeadersTable } from "./HeadersTable.tsx"

export function TransactionMessagePanel({
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
          {title} <span className="text-gray-400">({truncate(messageId || "-", 7)})</span>
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
