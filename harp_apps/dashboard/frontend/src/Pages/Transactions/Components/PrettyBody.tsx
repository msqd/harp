import { useState } from "react"
import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light"
import BaseStyle from "react-syntax-highlighter/dist/esm/styles/prism/vs"
import { Button } from "ui/Components/Button"
const Style = { ...BaseStyle }

export function PrettyBody({
  content = null,
  contentType = null,
}: {
  content: string | null
  contentType?: string | null
}) {
  const [visibleContent, setVisibleContent] = useState(content?.slice(0, 8000))
  const loadAllContent = () => setVisibleContent(content!)

  switch (contentType) {
    case "application/json":
      return (
        <>
          <SyntaxHighlighter
            language="javascript"
            className="w-fit overflow-x-auto text-black language-javascript max-w-full text-xs"
            children={visibleContent || ""}
            style={Style}
            customStyle={{ padding: 0, border: 0 }}
          />
          {(visibleContent?.length ?? 0) < (content?.length || 0) && (
            <div className="flex w-full justify-end mb-2">
              <Button variant="secondary" onClick={loadAllContent}>
                Load all
              </Button>
            </div>
          )}
        </>
      )
  }

  return content ? (
    <pre className="max-w-full overflow-x-auto p-4 text-xs text-black" style={{ padding: 0, border: 0 }}>
      {content}
    </pre>
  ) : null
}
