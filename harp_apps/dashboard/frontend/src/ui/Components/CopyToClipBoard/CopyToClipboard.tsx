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

  const handleCopy = () => {
    if (text) {
      navigator.clipboard
        .writeText(text)
        .then(() => {
          setCopySuccess(true)
          setTimeout(() => setCopySuccess(false), 2000)
        })
        .catch((err) => {
          console.error("Copy failed!", err)
          setCopySuccess(false)
        })
    } else if (targetRef) {
      if (targetRef.current) {
        if (contentType === "html") {
          const html = targetRef.current.innerHTML
          const blob = new Blob([html], { type: "text/html" })
          const data = [new ClipboardItem({ "text/html": blob })]

          navigator.clipboard
            .write(data)
            .then(() => {
              setCopySuccess(true)
              setTimeout(() => setCopySuccess(false), 2000)
            })
            .catch((err) => {
              console.error("Copy failed!", err)
              setCopySuccess(false)
            })
        } else {
          const text = targetRef.current.textContent || ""

          navigator.clipboard
            .writeText(text)
            .then(() => {
              setCopySuccess(true)
              setTimeout(() => setCopySuccess(false), 2000)
            })
            .catch((err) => {
              console.error("Copy failed!", err)
              setCopySuccess(false)
            })
        }
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
