import { NotFound } from "./NotFound"

const backLink = (
  <a href="/" className="text-sm font-semibold text-blue-600 hover:text-blue-500">
    Back to the overview
  </a>
)

export const Page = () => (
  <NotFound title="Page not found" action={backLink}>
    This page does not exist. The address may be mistyped, or the link outdated.
  </NotFound>
)

export const Transaction = () => (
  <NotFound title="Transaction not found" action={backLink}>
    This transaction does not exist or has been removed.
  </NotFound>
)

export const WithoutAction = () => <NotFound title="Transaction not found">Nothing to see here.</NotFound>
