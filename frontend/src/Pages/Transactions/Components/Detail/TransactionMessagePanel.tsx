import { ReactNode } from "react"
import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light"
import BaseStyle from "react-syntax-highlighter/dist/esm/styles/prism/vs"

import { H4 } from "mkui/Components/Typography"

const Style = { ...BaseStyle }

function PrettyBody({ content = null, contentType = null }: { content: string | null; contentType: string | null }) {
  switch (contentType) {
    case "application/json":
      return (
        <SyntaxHighlighter
          language="javascript"
          className="w-fit overflow-x-auto p-4 text-sm text-black language-javascript max-w-full"
          children={content || ""}
          style={Style}
          customStyle={{ fontSize: "0.9rem", padding: 0, border: 0 }}
        />
      )
  }

  return content ? (
    <pre
      className="max-w-full overflow-x-auto p-4 text-sm text-black"
      style={{ fontSize: "0.8rem", padding: 0, border: 0 }}
    >
      {content}
    </pre>
  ) : null
}

export function TransactionMessagePanel({
  children,
  headers = null,
  body = null,
  contentType = null,
}: {
  messageId: string | null
  headers?: string | null
  body?: string | null
  contentType?: string | null
  children?: ReactNode
}) {
  return (
    <div className="flex-none overflow-none px-1 max-w-full">
      {children}
      <div className="w-full max-w-full overflow-auto">
        <H4>Headers</H4>
        <table className="divide-y divide-gray-100 border mb-4">
          {headers
            ? headers.split("\n").map((line) => {
                const s = line.split(":", 2)
                return (
                  <tr>
                    <td className="px-2 py1">{s[0]}</td>
                    <td className="px-2 py1">{s[1]}</td>
                  </tr>
                )
              })
            : null}
        </table>
        <H4>Body {contentType ? `(${contentType})` : null}</H4>
        <PrettyBody content={body} contentType={contentType} />
      </div>
    </div>
  )
}
