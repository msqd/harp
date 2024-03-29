import { ClipboardDocumentIcon, ClipboardDocumentCheckIcon } from "@heroicons/react/24/outline"
import { useRef, useState } from "react"

export function CopyToClipboardWrapper({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const [copySuccess, setCopySuccess] = useState(false)

  const handleCopy = () => {
    const text = ref.current?.textContent || ""
    navigator.clipboard
      .writeText(text)
      .then(() => setCopySuccess(true))
      .catch((err) => {
        console.error("Copy failed!", err)
        setCopySuccess(false)
      })
  }

  return (
    <div className="flex flex-col">
      {copySuccess ? (
        <ClipboardDocumentCheckIcon className="h-4 w-4 cursor-pointe text-gray-400" />
      ) : (
        <ClipboardDocumentIcon className="h-4 w-4 cursor-pointer text-gray-400" onClick={handleCopy} />
      )}
      <div ref={ref}>{children}</div>
    </div>
  )
}
