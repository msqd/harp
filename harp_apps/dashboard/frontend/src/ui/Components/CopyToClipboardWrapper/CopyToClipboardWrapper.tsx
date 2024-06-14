import { useRef, useState } from "react"
import { ClipboardDocumentIcon, ClipboardDocumentCheckIcon } from "@heroicons/react/24/outline"

interface CopyToClipboardWrapperProps {
  children: React.ReactNode
}

export function CopyToClipboardWrapper({ children }: CopyToClipboardWrapperProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [copySuccess, setCopySuccess] = useState(false)

  const handleCopy = () => {
    if (ref.current) {
      const html = ref.current.innerHTML
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
    }
  }

  const Icon = copySuccess ? ClipboardDocumentCheckIcon : ClipboardDocumentIcon

  return (
    <div className="flex flex-col items-start top-1">
      <Icon
        title="Copy to clipboard"
        className={`m-2 h-4 w-4 cursor-pointer ${copySuccess ? "text-blue-300" : "text-gray-500"}`}
        onClick={handleCopy}
      />
      <div ref={ref}>{children}</div>
    </div>
  )
}
