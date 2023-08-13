import { ReactElement } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  UseQueryResult,
} from "react-query";
import { ReactQueryDevtools } from "react-query/devtools";
import { QueryObserverSuccessResult } from "react-query/types/core/types";
import NavBar from "./Components/Layout/NavBar.tsx";
import TransactionList from "./TransactionList.tsx";

function OnQuerySuccess<T>({
  query,
  children,
}: {
  query: UseQueryResult<T>;
  children: (query: QueryObserverSuccessResult<T>) => ReactElement;
}) {
  if (query.isLoading) {
    return <div>Loading...</div>;
  }

  if (query.isError || !query.isSuccess) {
    return <div>Error!</div>;
  }

  return children(query);
}

interface ItemList<T> {
  items: T[];
}

interface Request {
  method: string;
  url: string;
  headers: any;
  body: any;
}

interface Response {
  statusCode: number;
  headers: any;
  body: any;
}
export interface Transaction {
  id: string;
  request: Request | null;
  response: Response | null;
  createdAt: string;
}

function List() {
  const query = useQuery<ItemList<Transaction>>("transactions", () =>
    fetch("http://localhost:4000/api/").then((r) => r.json()),
  );

  return (
    <OnQuerySuccess query={query}>
      {(query) => <TransactionList transactions={query.data.items} />}
    </OnQuerySuccess>
  );
}

function App() {
  return (
    <>
      <NavBar></NavBar>
      <div className="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
        <List />
      </div>
    </>
  );
}

export default App;
