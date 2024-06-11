import { useState } from "react"
import { QueryObserverSuccessResult } from "react-query/types/core/types"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { ItemList } from "Domain/Api/Types"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { Transaction } from "Models/Transaction"
import { Filters } from "Types/filters"

import {
  DetailsCloseButton,
  FiltersHideButton,
  FiltersResetButton,
  FiltersShowButton,
  OpenInNewWindowLink,
} from "./Components/Buttons.tsx"
import { TransactionDataTable } from "./Components/List/index.ts"
import { FiltersSidebar } from "./Containers/index.ts"
import { TransactionDetailOnQuerySuccess } from "./TransactionDetailOnQuerySuccess.tsx"

export function TransactionListOnQuerySuccess({
  query,
  filters,
}: {
  query: QueryObserverSuccessResult<ItemList<Transaction> & { total: number; pages: number; perPage: number }>
  filters: Filters
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [selected, setSelected] = useState<Transaction | null>(null)
  const selectedId = searchParams.get("selected")
  const hasSelection = !!selectedId
  const [isFiltersOpen, setIsFiltersOpen] = useState(true)
  const detailQuery = useTransactionsDetailQuery(selectedId!)

  const resetFilters = () => {
    searchParams.delete("endpoint")
    searchParams.delete("method")
    searchParams.delete("status")
    searchParams.delete("flag")
    navigate(
      {
        pathname: location.pathname,
        search: searchParams.toString(),
      },
      { replace: false },
    )
  }

  const updateQueryParam = (paramName: string, paramValue: string | undefined) => {
    if (paramValue) {
      searchParams.set(paramName, paramValue)
    } else {
      searchParams.delete(paramName)
    }

    navigate(
      {
        pathname: location.pathname,
        search: searchParams.toString(),
      },
      { replace: false },
    )
  }

  return (
    <div className="flex w-full items-start gap-x-8 relative">
      {isFiltersOpen ? (
        <aside className="sticky top-8 hidden w-1/5 min-w-40 max-w-60 2xl:min-w-52 2xl:max-w-72 shrink-0 lg:block">
          <div className="text-right">
            <FiltersResetButton onClick={resetFilters} />
            <FiltersHideButton onClick={() => setIsFiltersOpen(false)} />
          </div>
          <FiltersSidebar filters={filters} />
        </aside>
      ) : (
        <FiltersShowButton onClick={() => setIsFiltersOpen(true)} />
      )}

      <main className="flex-1 overflow-auto">
        <TransactionDataTable
          transactions={query.data.items}
          onSelectionChange={(newSelected) =>
            newSelected && newSelected.id && (!hasSelection || selected?.id != newSelected.id)
              ? (setSelected(newSelected), updateQueryParam("selected", newSelected.id))
              : (setSelected(null), updateQueryParam("selected", undefined))
          }
          selected={selected ? selected : undefined}
        />
      </main>

      {hasSelection ? (
        <aside className="sticky top-8 w-2/5 min-w-96 shrink-0 block">
          <div className="text-right">
            <OpenInNewWindowLink id={selectedId} />
            <DetailsCloseButton onClick={() => (setSelected(null), updateQueryParam("selected", undefined))} />
          </div>

          <OnQuerySuccess
            query={detailQuery}
            onQueryError={() => (setSelected(null), updateQueryParam("selected", undefined))}
          >
            {(query) => {
              return <TransactionDetailOnQuerySuccess query={query} />
            }}
          </OnQuerySuccess>
        </aside>
      ) : null}
    </div>
  )
}
