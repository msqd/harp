import { ClipboardDocumentIcon, ClipboardDocumentCheckIcon } from "@heroicons/react/24/outline"
import { useState } from "react"

import { classNames } from "ui/Utilities"

interface CopyToClipboardProps {
  text?: string
  targetRef?: React.RefObject<HTMLElement>
  className?: string
  contentType?: string
  description?: string
}

const CopyToClipboard: React.FC<CopyToClipboardProps> = ({ text, targetRef, className, contentType, description }) => {
  const [copySuccess, setCopySuccess] = useState(false)
  const canCopy = navigator.clipboard

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
      if (contentType?.includes("html")) {
        const html = targetRef.current.innerHTML
        const blob = new Blob([html], { type: contentType })
        const data = [new ClipboardItem({ [contentType]: blob })]

        handleClipboardWrite(data)
      } else if (contentType?.startsWith("text/") || contentType?.startsWith("application/")) {
        const text = targetRef.current.innerText || ""
        handleClipboardWrite(text)
      }
    }
  }

  const Icon = copySuccess ? ClipboardDocumentCheckIcon : ClipboardDocumentIcon

  return canCopy && (!contentType || contentType.startsWith("text/") || contentType.startsWith("application/")) ? (
    <div className={classNames("flex items-center -space-x-1 text-xs", className)} onClick={handleCopy}>
      {description && (
        <span className={`m-2 cursor-pointer ${copySuccess ? "text-blue-300" : "text-gray-500"}`}>{description}</span>
      )}
      <Icon
        title="Copy to clipboard"
        className={`m-2 h-4 w-4 cursor-pointer ${copySuccess ? "text-blue-300" : "text-gray-500"}`}
      />
    </div>
  ) : null
}

export default CopyToClipboard
