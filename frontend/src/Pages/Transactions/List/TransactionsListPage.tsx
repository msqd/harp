import { useQuery } from "react-query"
import { ItemList } from "Domain/Api"
import { Transaction } from "Domain/Transactions"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { TransactionsList } from "./TransactionsList.tsx"
import { useTransactionsListQuery } from "Domain/Transactions"

function TransactionsListPage() {
  const query = useTransactionsListQuery()

  return (
    <OnQuerySuccess query={query}>{(query) => <TransactionsList transactions={query.data.items} />}</OnQuerySuccess>
  )
}

export default TransactionsListPage
