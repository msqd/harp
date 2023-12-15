import { ComponentType, ReactNode } from "react"

export function TransactionMessagePanel({
  title,
  headers = null,
  body = null,
}: {
  Icon: ComponentType<any>
  //message: TransactionMessage | Record<string, never> | null
  messageId: string | null
  title: ReactNode
  headers?: string | null
  body?: string | null
}) {
  return (
    <div className="flex-none w-1/2 overflow-none max-h-screen px-1">
      <h4 className="text-sm font-semibold leading-6 text-gray-900">{title}</h4>
      <div className="w-full overflow-auto">
        <h5 className="text-sm font-semibold leading-6 text-gray-900">Headers</h5>
        {headers ? <pre>{headers}</pre> : null}
        <h5 className="text-sm font-semibold leading-6 text-gray-900">Body</h5>
        {body ? <pre>{body}</pre> : null}
        {/*
            <HeadersTable headers={message.headers || {}} />
            <SyntaxHighlighter
              language="javascript"
              className="w-fit overflow-x-auto p-4 text-xs text-black language-javascript"
              children={message.content || ""}
            />
*/}
      </div>
    </div>
  )
}
