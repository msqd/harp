import { ComponentType, ReactNode } from "react"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vs } from "react-syntax-highlighter/dist/esm/styles/prism"

function _render(content: string | null, contentType: string | null) {
  switch (contentType) {
    case "application/json":
      return (
        <SyntaxHighlighter
          language="javascript"
          className="w-fit overflow-x-auto p-4 font-medium text-black language-javascript"
          children={content || ""}
          style={vs}
          customStyle={{ fontSize: "0.9rem", padding: 0, border: 0 }}
        />
      )
  }
  return content ? <pre>{content}</pre> : null
}

export function TransactionMessagePanel({
  title,
  headers = null,
  body = null,
  contentType = null,
}: {
  Icon: ComponentType
  messageId: string | null
  title: ReactNode
  headers?: string | null
  body?: string | null
  contentType?: string | null
}) {
  return (
    <div className="flex-none w-1/2 overflow-none max-h-screen px-1">
      <h4 className="text-sm font-semibold leading-6 text-gray-900">{title}</h4>
      <div className="w-full overflow-auto">
        <h5 className="text-sm font-semibold leading-6 text-gray-900">Headers</h5>
        {headers ? <pre>{headers}</pre> : null}
        <h5 className="text-sm font-semibold leading-6 text-gray-900">
          Body {contentType ? `(${contentType})` : null}
        </h5>
        {_render(body, contentType)}

        {/*
            <HeadersTable headers={message.headers || {}} />
*/}
      </div>
    </div>
  )
}
