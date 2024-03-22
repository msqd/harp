import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light"
import BaseStyle from "react-syntax-highlighter/dist/esm/styles/prism/vs"

const Style = { ...BaseStyle }

export function PrettyBody({
  content = null,
  contentType = null,
}: {
  content: string | null
  contentType?: string | null
}) {
  switch (contentType) {
    case "application/json":
      return (
        <SyntaxHighlighter
          language="javascript"
          className="w-fit overflow-x-auto text-black language-javascript max-w-full text-xs"
          children={content || ""}
          style={Style}
          customStyle={{ padding: 0, border: 0 }}
        />
      )
  }

  return content ? (
    <pre className="max-w-full overflow-x-auto p-4 text-xs text-black" style={{ padding: 0, border: 0 }}>
      {content}
    </pre>
  ) : null
}
