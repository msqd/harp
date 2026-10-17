import { MemoryRouter } from "react-router-dom"

import { Pane } from "ui/Components/Pane"

import { CopyTransactionLinkButton, OpenInNewWindowLink } from "./Buttons"

export const TransactionLinks = () => (
  <MemoryRouter>
    <Pane className="flex items-center gap-4">
      <CopyTransactionLinkButton url={`${window.location.origin}/transactions/ABCD1234`} />
      <OpenInNewWindowLink id="ABCD1234" />
    </Pane>
  </MemoryRouter>
)
