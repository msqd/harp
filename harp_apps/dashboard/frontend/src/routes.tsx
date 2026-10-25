import { lazy, Suspense } from "react"
import { RouteObject } from "react-router"

import { Layout } from "Components/Layout"
import { TransactionDataTable } from "Pages/Transactions/Components/List"

import { NotFoundPage, RouteError } from "./RouteElements"

const TransactionListPage = lazy(() => import("./Pages/Transactions/TransactionListPage"))

export const navigationItems = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system", requires: "editor" as const },
  { label: "Audit", to: "/audit", requires: "admin" as const },
  { label: "My account", to: "/account" },
]

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
          {
            path: "audit",
            Component: lazy(() => import("./Pages/Audit/AuditPage")),
          },
          {
            path: "account",
            Component: lazy(() => import("./Pages/Account/AccountPage")),
          },
          { path: "*", Component: NotFoundPage },
        ],
      },
    ],
  },
]
