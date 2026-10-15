import { useEffect } from "react"
import { Link, useRouteError } from "react-router-dom"

import { Error as ErrorDetails, Page } from "Components/Page"
import { NotFound } from "ui/Components/NotFound"

function BackToOverview() {
  return (
    <Link to="/" className="text-sm font-semibold text-blue-600 hover:text-blue-500">
      Back to the overview
    </Link>
  )
}

export function NotFoundPage() {
  return (
    <Page>
      <NotFound title="Page not found" action={<BackToOverview />}>
        This page does not exist. The address may be mistyped, or the link outdated.
      </NotFound>
    </Page>
  )
}

/** Unexpected errors keep their details (and reach the console) instead of masquerading as a 404. */
export function RouteError() {
  const error = useRouteError()
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <Page>
      <ErrorDetails
        error={error instanceof Error ? error : new Error(String(error))}
        resetErrorBoundary={() => window.location.reload()}
      />
    </Page>
  )
}
