import { ComponentType, ReactNode } from "react"
import { TransactionMessage } from "Domain/Transactions/OldDeprecatedTypes"
import { HeadersTable } from "./Components/HeadersTable.tsx"
import { LightAsync as SyntaxHighlighter } from "react-syntax-highlighter"

export function TransactionMessagePanel({
  title,
  message,
}: {
  Icon: ComponentType<any>
  message: TransactionMessage | Record<string, never> | null
  messageId: string | null
  title: ReactNode
}) {
  return (
    <div className="flex-none w-1/2 overflow-none max-h-screen px-1">
      <h4 className="text-sm font-semibold leading-6 text-gray-900">{title}</h4>
      <div className="w-full overflow-auto">
        {message == null ? (
          <div>Loading...</div>
        ) : (
          <>
            <HeadersTable headers={message.headers || {}} />
            <SyntaxHighlighter
              language="javascript"
              className="w-fit overflow-x-auto p-4 text-xs text-black language-javascript"
              children={message.content || ""}
            />
          </>
        )}
      </div>
    </div>
  )
}
