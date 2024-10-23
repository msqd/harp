import { ClipboardDocumentIcon, ClipboardDocumentCheckIcon } from "@heroicons/react/24/outline"
import { useState } from "react"

import { classNames } from "ui/Utilities"

interface CopyToClipboardProps {
  text?: string
  targetRef?: React.RefObject<HTMLElement>
  className?: string
  contentType?: "text" | "html"
}

const CopyToClipboard: React.FC<CopyToClipboardProps> = ({ text, targetRef, className, contentType = "text" }) => {
  const [copySuccess, setCopySuccess] = useState(false)

  const handleClipboardWrite = (clipboardData: string | ClipboardItem[]) => {
    const writePromise =
      typeof clipboardData === "string"
        ? navigator.clipboard.writeText(clipboardData)
        : navigator.clipboard.write(clipboardData)

    writePromise
      .then(() => {
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
      })
      .catch((err) => {
        console.error("Copy failed!", err)
        setCopySuccess(false)
      })
  }

  const handleCopy = () => {
    if (text) {
      handleClipboardWrite(text)
    } else if (targetRef?.current) {
      if (contentType === "html") {
        const html = targetRef.current.innerHTML
        const blob = new Blob([html], { type: "text/html" })
        const data = [new ClipboardItem({ "text/html": blob })]

        handleClipboardWrite(data)
      } else {
        const text = targetRef.current.textContent || ""
        handleClipboardWrite(text)
      }
    }
  }

  const Icon = copySuccess ? ClipboardDocumentCheckIcon : ClipboardDocumentIcon

  return (
    <Icon
      title="Copy to clipboard"
      className={classNames(className, `m-2 h-4 w-4 cursor-pointer ${copySuccess ? "text-blue-300" : "text-gray-500"}`)}
      onClick={handleCopy}
    />
  )
}

export default CopyToClipboard
