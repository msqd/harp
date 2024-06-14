import { useRef } from "react"

import CopyToClipboard from "./CopyToClipboard"

export const Default = () => {
  const ref = useRef<HTMLDivElement>(null)

  return (
    <>
      <CopyToClipboard targetRef={ref} className="mb-2" />
      <div ref={ref}>Text that shall be copied</div>

      <input type="text" placeholder="Paste here" className="mt-2 p-1 border border-gray-300 rounded" />
    </>
  )
}
