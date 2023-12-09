import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { TransactionsList } from "./Components/TransactionsList.tsx"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Page } from "Components/Page"

function TransactionsListPage() {
  const query = useTransactionsListQuery()

  return (
    <Page>
      <OnQuerySuccess query={query}>
        {(query) => {
          return <TransactionsList transactions={query.data.items} />
        }}
      </OnQuerySuccess>
    </Page>
  )
}

export default TransactionsListPage
