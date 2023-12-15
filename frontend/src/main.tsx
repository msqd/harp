import ReactDOM from "react-dom/client"
import { QueryClient, QueryClientProvider } from "react-query"
import { ReactQueryDevtools } from "react-query/devtools"
import { createBrowserRouter, RouterProvider } from "react-router-dom"
import GlobalStyles from "Styles/GlobalStyles"
import { Layout } from "Components/Layout"
import { TransactionsRoute } from "./Routes"
import TransactionsListPage from "./Pages/Transactions/List/TransactionsListPage"
import { ProxySettings } from "Pages/ProxySettings"
import { Dashboard } from "Pages/Dashboard"
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
    path: "/transactions",
    element: <TransactionsRoute />,
  },
  {
    path: "/settings",
    element: <ProxySettings />,
  },
])
const queryClient = new QueryClient()

// @ts-ignore
const Root = React.StrictMode

ReactDOM.createRoot(document.getElementById("root")!).render(
  <Root>
    <QueryClientProvider client={queryClient}>
      <GlobalStyles />
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </Root>,
)
