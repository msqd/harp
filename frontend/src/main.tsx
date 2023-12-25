import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { QueryClient, QueryClientProvider } from "react-query"
import { ReactQueryDevtools } from "react-query/devtools"
import { createBrowserRouter, RouterProvider } from "react-router-dom"

import { Layout } from "Components/Layout"
import { Dashboard } from "Pages/Dashboard"
import { ProxySettings } from "Pages/ProxySettings"
import GlobalStyles from "Styles/GlobalStyles"

import { TransactionsListPage } from "./Pages/Transactions"

import "./index.css"

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        path: "",
        element: <Dashboard />,
      },
      {
        path: "transactions",
        element: <TransactionsListPage />,
      },
      {
        path: "settings",
        element: <ProxySettings />,
      },
    ],
  },
  {
    path: "/settings",
    element: <ProxySettings />,
  },
])
const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <GlobalStyles />
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </StrictMode>,
)
