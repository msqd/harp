import { lazy, StrictMode, Suspense } from "react"
import { createRoot } from "react-dom/client"
import { QueryClient, QueryClientProvider } from "react-query"
import { ReactQueryDevtools } from "react-query/devtools"
import { createBrowserRouter, RouterProvider } from "react-router-dom"

import { Layout } from "Components/Layout"
import { TransactionDataTable } from "Pages/Transactions/Components/List"
import GlobalStyles from "Styles/GlobalStyles"
import "./index.css"

const TransactionListPage = lazy(() => import("./Pages/Transactions/TransactionListPage"))

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout title="HARP EA" />,
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
    ],
  },
])
const queryClient = new QueryClient()

// Enable mocking in development using msw server set up for the browser
async function enableMocking() {
  if (process.env.DISABLE_MOCKS == "true" || process.env.NODE_ENV !== "development") {
    return
  }

  const { worker, http, HttpResponse } = await import("./tests/mocks/browser")

  // @ts-expect-error This is a wanted violation of Window type, as it is a special env for browser tests.
  // Propagate the worker and `http` references to be globally available.
  // This would allow to modify request handlers on runtime.
  window.msw = {
    worker,
    http,
    HttpResponse,
  }
  return worker.start()
}

void enableMocking().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <GlobalStyles />
        <RouterProvider router={router} />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </StrictMode>,
  )
})
