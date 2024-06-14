import { CopyToClipboardWrapper } from "./CopyToClipboardWrapper"

export const Default = () => (
  <>
    <CopyToClipboardWrapper>
      <div>Text that shall be copied</div>
    </CopyToClipboardWrapper>

    <input type="text" placeholder="Paste here" className="mt-2 p-1 border border-gray-300 rounded" />
  </>
)
