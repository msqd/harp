import { useEffect, useState } from "react"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Filters } from "Types/filters"
import { Paginator } from "mkui/Components/Pagination"

import { TransactionDataTable } from "./Components/List"
import { FiltersSidebar } from "./Containers"
import { TransactionDetailPanel } from "./TransactionDetailPanel.tsx"

import { Transaction } from "../../Models/Transaction"

export function TransactionListPage() {
  const [filters, setFilters] = useState<Filters>({})
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Transaction | null>(null)
  const hasSelection = selected && selected.id
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const query = useTransactionsListQuery({ filters, page, cursor })

  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length) {
      setCursor(query.data.items[0].id)
    }
  }, [page, query])

  useEffect(() => {
    const handleClick = () => {
      setSelected(null)
    }
    document.body.addEventListener("click", handleClick)

    return () => {
      document.body.removeEventListener("click", handleClick)
    }
  }, [])

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
            <div className={hasSelection ? "" : "row-end-1 col-start-2 col-span-4"}>
              {(paginatorProps.total || 0) > 0 ? (
                <Paginator {...paginatorProps} showSummary={false} className={hasSelection ? "invisible" : ""} />
              ) : null}
              <TransactionDataTable
                transactions={query.data.items}
                onSelectionChange={(selected) => setSelected(selected)}
                selected={selected && selected.id ? selected : undefined}
              />
              {(paginatorProps.total || 0) > 0 ? (
                <Paginator {...paginatorProps} className={hasSelection ? "invisible" : ""} />
              ) : null}
            </div>
            {hasSelection ? null : (
              <div className="col-start-1 col-span-1">
                <FiltersSidebar filters={filters} setFilters={setFilters} />
              </div>
            )}

            {selected && selected.id ? <TransactionDetailPanel id={selected.id} /> : null}
          </div>
        )}
      </OnQuerySuccess>
    </Page>
  )
}
