import { useEffect, useState } from "react"

import { Page } from "Components/Page"
import { PageTitle } from "Components/Page/PageTitle.tsx"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Filters } from "Types/filters"
import { SearchBar } from "ui/Components/SearchBar/SearchBar.tsx"

import { OptionalPaginator } from "./Components/OptionalPaginator.tsx"
import { TransactionListOnQuerySuccess } from "./TransactionListOnQuerySuccess.tsx"

export function TransactionListPage() {
  const [filters, setFilters] = useState<Filters>({})
  const [page, setPage] = useState(1)
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const [search, setSearch] = useState<string | undefined>(undefined)
  const query = useTransactionsListQuery({ filters, page, cursor, search })

  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length) {
      setCursor(query.data.items[0].id)
    }
  }, [page, query])

  return (
    <Page
      title={
        <PageTitle title="Transactions" description="Explore transactions that went through the proxy">
          {query.isSuccess ? (
            <OptionalPaginator
              current={page}
              setPage={setPage}
              total={query.data.total}
              pages={query.data.pages}
              perPage={query.data.perPage}
            />
          ) : null}
        </PageTitle>
      }
    >
      <SearchBar placeHolder="Search transactions" setSearch={setSearch} className="w-1/2" />
      <OnQuerySuccess query={query}>
        {(query) => <TransactionListOnQuerySuccess query={query} filters={filters} setFilters={setFilters} />}
      </OnQuerySuccess>
    </Page>
  )
}
