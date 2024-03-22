import { useState } from "react"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { ItemList } from "Domain/Api/Types"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { Transaction } from "Models/Transaction"
import { Filters } from "Types/filters"

import { DetailsCloseButton, FiltersHideButton, FiltersShowButton, OpenInNewWindowLink } from "./Components/Buttons.tsx"
import { TransactionDataTable } from "./Components/List"
import { FiltersSidebar } from "./Containers"
import { TransactionDetailOnQuerySuccess } from "./TransactionDetailOnQuerySuccess.tsx"

export function TransactionListOnQuerySuccess({
  query,
  filters,
  setFilters,
}: {
  query: QueryObserverSuccessResult<ItemList<Transaction> & { total: number; pages: number; perPage: number }>
  filters: Filters
  setFilters: (filters: Filters) => void
}) {
  const [selected, setSelected] = useState<Transaction | null>(null)
  const hasSelection = selected && selected.id
  const [isFiltersOpen, setIsFiltersOpen] = useState(true)
  const detailQuery = useTransactionsDetailQuery(selected?.id)

  return (
    <div className="flex w-full items-start gap-x-8 relative">
      {isFiltersOpen ? (
        <aside className="sticky top-8 hidden w-1/5 min-w-56 max-w-96 shrink-0 lg:block">
          <div className="text-right">
            <FiltersHideButton onClick={() => setIsFiltersOpen(false)} />
          </div>
          <FiltersSidebar filters={filters} setFilters={setFilters} />
        </aside>
      ) : (
        <FiltersShowButton onClick={() => setIsFiltersOpen(true)} />
      )}

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
      </main>

      {hasSelection ? (
        <aside className="sticky top-8 w-2/5 min-w-96 shrink-0 block">
          <div className="text-right">
            <OpenInNewWindowLink id={selected.id!} />
            <DetailsCloseButton onClick={() => setSelected(null)} />
          </div>
          <OnQuerySuccess query={detailQuery}>
            {(query) => <TransactionDetailOnQuerySuccess query={query} />}
          </OnQuerySuccess>
        </aside>
      ) : null}
    </div>
  )
}
