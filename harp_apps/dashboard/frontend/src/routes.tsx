import { lazy, Suspense, useEffect } from "react"
import { Link, RouteObject, useRouteError } from "react-router-dom"

import { Layout } from "Components/Layout"
import { Error as ErrorDetails, Page } from "Components/Page"
import { TransactionDataTable } from "Pages/Transactions/Components/List"
import { NotFound } from "ui/Components/NotFound"

const TransactionListPage = lazy(() => import("./Pages/Transactions/TransactionListPage"))

export const navigationItems = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system" },
]

const BackToOverview = () => (
  <Link to="/" className="text-sm font-semibold text-blue-600 hover:text-blue-500">
    Back to the overview
  </Link>
)

function NotFoundPage() {
  return (
    <Page>
      <NotFound title="Page not found" action={<BackToOverview />}>
        This page does not exist. The address may be mistyped, or the link outdated.
      </NotFound>
    </Page>
  )
}

/** Unexpected errors keep their details (and reach the console) instead of masquerading as a 404. */
function RouteError() {
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

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout navigationItems={navigationItems} />,
    children: [
      {
        // Pathless wrapper: errors render inside the layout, not instead of it.
        errorElement: <RouteError />,
        children: [
          {
            path: "",
            Component: lazy(() => import("./Pages/Overview/OverviewPage")),
          },
          {
            path: "transactions/:id",
            Component: lazy(() => import("./Pages/Transactions/TransactionDetailPage")),
          },
          {
            path: "transactions",
            element: (
              <Suspense fallback={<div>Loading...</div>}>
                <TransactionListPage TransactionDataTable={TransactionDataTable} />
              </Suspense>
            ),
          },
          {
            path: "system",
            Component: lazy(() => import("./Pages/System/SystemPage")),
          },
          { path: "*", Component: NotFoundPage },
        ],
      },
    ],
  },
]
