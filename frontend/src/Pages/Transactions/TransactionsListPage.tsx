import { useEffect, useState } from "react"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Filters } from "Types/filters"
import { Paginator } from "mkui/Components/Pagination"

import { TransactionDataTable } from "./Components/List"
import { FiltersSidebar } from "./Containers"

export function TransactionsListPage() {
  const [filters, setFilters] = useState<Filters>({})
  const [page, setPage] = useState(1)
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const query = useTransactionsListQuery({ filters, page, cursor })

  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length) {
      setCursor(query.data.items[0].id)
    }
  }, [page, query])

  const paginatorProps = {
    current: page,
    setPage: setPage,
    total: query.isSuccess ? query.data.total ?? undefined : undefined,
    pages: query.isSuccess ? query.data.pages ?? undefined : undefined,
    perPage: query.isSuccess ? query.data.perPage ?? undefined : undefined,
  }

  return (
    <Page title="Transactions" description="Explore transactions that went through the proxy">
      <OnQuerySuccess query={query}>
        {(query) => (
          <div className="w-full grid grid-cols-1 grid-rows-1 items-start gap-x-8 gap-y-8 lg:mx-0 lg:max-w-none lg:grid-cols-5">
            <div className="col-start-2 col-span-4 row-end-1">
              {(paginatorProps.total || 0) > 0 ? <Paginator {...paginatorProps} showSummary={false} /> : null}
              <TransactionDataTable transactions={query.data.items} />
              {(paginatorProps.total || 0) > 0 ? <Paginator {...paginatorProps} /> : null}
            </div>
            <div className="col-start-1 col-span-1">
              <FiltersSidebar filters={filters} setFilters={setFilters} />
            </div>
          </div>
        )}
      </OnQuerySuccess>
    </Page>
  )
}
