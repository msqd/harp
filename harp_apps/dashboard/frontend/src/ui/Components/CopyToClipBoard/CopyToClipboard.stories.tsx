import { useRef } from "react"
import CopyToClipboard from "./CopyToClipboard"

export const Default = () => {
  const ref = useRef<HTMLDivElement>(null)
  // console.log(ref.current)
  // const html = ref.current.innerHTML
  // const blob = new Blob([html], { type: "text/html" })
  // const data = [new ClipboardItem({ "text/html": blob })]

  // console.log(data)
  return (
    <>
      <CopyToClipboard targetRef={ref} className="mb-2" />
      <div ref={ref}>Text that shall be copied</div>

      <input type="text" placeholder="Paste here" className="mt-2 p-1 border border-gray-300 rounded" />
    </>
  )
}
