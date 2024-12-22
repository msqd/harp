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
  NextButton,
  OpenInNewWindowLink,
  PreviousButton,
  VerticalFiltersShowButton,
} from "./Components/Buttons.tsx"
import { TransactionsDataTableProps } from "./Components/List/TransactionDataTable.tsx"
import { FiltersSidebar } from "./Containers"
import { TransactionDetailOnQuerySuccess } from "./TransactionDetailOnQuerySuccess.tsx"

export function TransactionListOnQuerySuccess({
  query,
  filters,
  TransactionDataTable,
}: {
  query: QueryObserverSuccessResult<ItemList<Transaction> & { total: number; pages: number; perPage: number }>
  filters: Filters
  TransactionDataTable: React.FC<TransactionsDataTableProps>
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const selectedIdFromUrl = searchParams.get("selected")
  const [selected, setLocalSelected] = useState<Transaction | null>(
    (selectedIdFromUrl ? query.data.items.find((item) => item.id === selectedIdFromUrl) : null) ?? null,
  )
  const selectedIndex = query.data.items.findIndex((item) => (selected ? item.id === selected.id : undefined))
  const hasSelection = selected && selected.id

  const setSelected = (newSelected?: Transaction | null) => {
    setLocalSelected(newSelected ?? null)
    updateQueryParam("selected", newSelected ? newSelected.id : undefined)
  }

  const [isFiltersOpen, setIsFiltersOpen] = useState(true)
  const detailQuery = useTransactionsDetailQuery(selected?.id ?? undefined)

  const resetFilters = (keys: string[]) => {
    keys.forEach((key) => searchParams.delete(key))
    navigate(
      {
        pathname: location.pathname,
        search: searchParams.toString(),
      },
      { replace: false },
    )
  }

  const resetAllFilters = () => {
    resetFilters(["endpoint", "method", "status", "flag", "tpdexmin", "tpdexmax"])
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
            <FiltersResetButton onClick={resetAllFilters} />
            <FiltersHideButton onClick={() => setIsFiltersOpen(false)} />
          </div>
          <FiltersSidebar filters={filters} />
        </aside>
      ) : (
        <VerticalFiltersShowButton onClick={() => setIsFiltersOpen(true)} />
      )}

      <main className="flex-1 overflow-auto">
        <TransactionDataTable
          transactions={query.data.items}
          onSelectionChange={(newSelected) =>
            newSelected && newSelected.id && (!hasSelection || selected.id != newSelected.id)
              ? setSelected(newSelected)
              : setSelected()
          }
          selected={selected ? selected : undefined}
        />
      </main>

      {hasSelection ? (
        <aside className="sticky top-8 w-2/5 min-w-96 shrink-0 block">
          <div className="flex mb-1">
            <div className="flex grow">
              {selectedIndex !== undefined && selectedIndex > 0 ? (
                <PreviousButton onClick={() => setSelected(query.data.items[selectedIndex - 1])} />
              ) : null}
              {selectedIndex !== undefined && selectedIndex >= 0 && selectedIndex < query.data.items.length - 1 ? (
                <NextButton onClick={() => setSelected(query.data.items[selectedIndex + 1])} />
              ) : null}
            </div>
            <div className="flex">
              {selected.id ? <OpenInNewWindowLink id={selected.id} /> : null}
              <DetailsCloseButton onClick={() => setSelected()} className="place-self-end" />
            </div>
          </div>

          <OnQuerySuccess query={detailQuery} onQueryError={() => setSelected()}>
            {(query) => {
              return <TransactionDetailOnQuerySuccess query={query} />
            }}
          </OnQuerySuccess>
        </aside>
      ) : null}
    </div>
  )
}
