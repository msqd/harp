import { ClipboardDocumentIcon, ClipboardDocumentCheckIcon } from "@heroicons/react/24/outline"
import { useRef, useState } from "react"

export function CopyToClipboardWrapper({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const [copySuccess, setCopySuccess] = useState(false)

  const handleCopy = () => {
    const text = ref.current?.textContent || ""
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
  return (
    <div className="flex flex-col items-start">
      {copySuccess ? (
        <ClipboardDocumentCheckIcon className="h-4 w-4 cursor-pointer text-blue-300" />
      ) : (
        <ClipboardDocumentIcon className="h-4 w-4 cursor-pointer text-gray-400" onClick={handleCopy} />
      )}
      <div ref={ref}>{children}</div>
    </div>
  )
}
