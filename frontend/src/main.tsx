import ReactDOM from "react-dom/client"
import { QueryClient, QueryClientProvider } from "react-query"
import { ReactQueryDevtools } from "react-query/devtools"
import { createBrowserRouter, RouterProvider } from "react-router-dom"
import GlobalStyles from "Styles/GlobalStyles"
import { Layout } from "Components/Layout"
import { DashboardRoute, TransactionsRoute } from "./Routes"
import TransactionsListPage from "./Pages/Transactions/List/TransactionsListPage"
import { Settings } from "Pages/ProxySettings"
import "./index.css"

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        path: "",
        element: <DashboardRoute />,
      },
      {
        path: "transactions",
        element: <TransactionsListPage />,
      },
      {
        path: "settings",
        element: <Settings/>,
      },
    ],
  },
  {
    path: "/transactions",
    element: <TransactionsRoute />,
  },
  {
    path: "/settings",
    element: <Settings/>,
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
