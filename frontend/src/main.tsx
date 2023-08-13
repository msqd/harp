import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "react-query";
import { ReactQueryDevtools } from "react-query/devtools";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import GlobalStyles from "Styles/GlobalStyles";

// main css
import "./index.css";
import { Layout } from "./Components/Layout";
import { DashboardRoute, TransactionsRoute } from "./Routes";

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
        element: <TransactionsRoute />,
      },
    ],
  },
  {
    path: "/transactions",
    element: <TransactionsRoute />,
  },
]);
const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <GlobalStyles />
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>,
);
