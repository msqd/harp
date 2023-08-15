import { useQuery } from "react-query";
import NavBar from "./Components/Layout/NavBar.tsx";
import { OnQuerySuccess } from "./Components/Utilities/OnQuerySuccess.tsx";
import { ItemList } from "./Domain/Api.tsx";
import { Transaction } from "./Domain/Transactions.tsx";
import TransactionsList from "./Pages/Transactions/List/TransactionsList.tsx";

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
