import { useEffect, useState } from "react"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { ItemList } from "Domain/Api/Types"
import { useTransactionsDetailQuery, useTransactionsListQuery } from "Domain/Transactions"
import { Transaction } from "Models/Transaction"
import { Filters } from "Types/filters"
import { Paginator } from "mkui/Components/Pagination"

import { TransactionDataTable } from "./Components/List"
import { FiltersSidebar } from "./Containers"
import { TransactionDetail } from "./Containers/Detail"

function TransactionListPageOnQuerySuccess({
  query,
  filters,
  setFilters,
  page,
  setPage,
}: {
  query: QueryObserverSuccessResult<ItemList<Transaction> & { total: number; pages: number; perPage: number }>
  filters: Filters
  setFilters: (filters: Filters) => void
  page: number
  setPage: (page: number) => void
}) {
  const [selected, setSelected] = useState<Transaction | null>(null)
  const hasSelection = selected && selected.id
  const detailQuery = useTransactionsDetailQuery(selected?.id)
  const paginatorProps = {
    current: page,
    setPage: setPage,
    total: query.isSuccess ? query.data.total ?? undefined : undefined,
    pages: query.isSuccess ? query.data.pages ?? undefined : undefined,
    perPage: query.isSuccess ? query.data.perPage ?? undefined : undefined,
  }
  return (
    <div className="flex w-full items-start gap-x-8 relative">
      <aside className="sticky top-8 hidden w-1/5 min-w-56 max-w-96 shrink-0 lg:block">
        <FiltersSidebar filters={filters} setFilters={setFilters} />
      </aside>

      <main className="flex-1 overflow-auto">
        <TransactionDataTable
          transactions={query.data.items}
          onSelectionChange={(newSelected) =>
            newSelected && newSelected.id && (!hasSelection || selected.id != newSelected.id)
              ? setSelected(newSelected)
              : setSelected(null)
          }
          selected={hasSelection ? selected : undefined}
        />

        {(paginatorProps.total || 0) > 0 ? (
          <Paginator {...paginatorProps} showSummary={false} className={hasSelection ? "invisible" : ""} />
        ) : null}
        {(paginatorProps.total || 0) > 0 ? (
          <Paginator {...paginatorProps} className={hasSelection ? "invisible" : ""} />
        ) : null}
      </main>

      {hasSelection ? (
        <aside className="sticky top-8 w-2/5 min-w-96 shrink-0 block">
          <OnQuerySuccess query={detailQuery}>
            {(query) => <TransactionDetail transaction={query.data} />}
          </OnQuerySuccess>
        </aside>
      ) : null}
    </div>
  )
}

export function TransactionListPage() {
  const [filters, setFilters] = useState<Filters>({})
  const [page, setPage] = useState(1)
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const query = useTransactionsListQuery({ filters, page, cursor })

  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length) {
      setCursor(query.data.items[0].id)
    }
  }, [page, query])

  return (
    <Page title="Transactions" description="Explore transactions that went through the proxy">
      <OnQuerySuccess query={query}>
        {(query) => (
          <TransactionListPageOnQuerySuccess
            query={query}
            filters={filters}
            setFilters={setFilters}
            page={page}
            setPage={setPage}
          />
        )}
      </OnQuerySuccess>
    </Page>
  )
}
