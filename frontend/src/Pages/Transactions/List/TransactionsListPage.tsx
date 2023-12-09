import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Page } from "Components/Page"
import { TransactionDataTable } from "./TransactionDataTable.tsx"

function TransactionsListPage() {
  const query = useTransactionsListQuery()

  return (
    <Page title="Transactions" description="Explore transactions that went through the proxy">
      <OnQuerySuccess query={query}>
        {(query) => {
          return <TransactionDataTable transactions={query.data.items} />
        }}
      </OnQuerySuccess>
    </Page>
  )
}

export default TransactionsListPage
