import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { ReactNode, useState } from "react"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

import { RequestMethodBadge } from "Components/Badges/RequestMethodBadge.tsx"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { ItemList } from "Domain/Api/Types"
import { useTransactionsDetailQuery } from "Domain/Transactions"
import { Transaction } from "Models/Transaction"
import { Filters } from "Types/filters"
import { ucfirst } from "Utils/Strings.ts"
import { Pane } from "mkui/Components/Pane"
import { H5 } from "mkui/Components/Typography"

import { PrettyBody } from "./Components/Detail/TransactionMessagePanel.tsx"
import { DetailsCloseButton, FiltersHideButton, FiltersShowButton } from "./Components/FiltersVisibilityButtons.tsx"
import { TransactionDataTable } from "./Components/List"
import { FiltersSidebar } from "./Containers"

import { ResponseStatusBadge } from "../../Components/Badges/ResponseStatusBadge.tsx"
import { KeyValueSettings } from "../../Domain/System/useSystemSettingsQuery.ts"
import { useBlobQuery } from "../../Domain/Transactions/useBlobQuery.tsx"
import { SettingsTable } from "../System/Components"

interface FoldableProps {
  open?: boolean
  title: ReactNode
  children: ReactNode
}

function Foldable({ open = true, title, children }: FoldableProps) {
  const [isOpen, setIsOpen] = useState(open)

  return (
    <div className="px-4 py-3">
      <H5 padding="pt-0" className="flex w-full cursor-pointer whitespace-nowrap" onClick={() => setIsOpen(!isOpen)}>
        {/* title (clickable) */}
        <div className="grow font-normal truncate">
          <span className="font-semibold">{title}</span>
        </div>

        {/* control to fold/unfold the content */}
        {isOpen ? (
          <ChevronUpIcon className="h-4 w-4 min-w-4 text-gray-600" />
        ) : (
          <ChevronDownIcon className="h-4 w-4 min-w-4 text-gray-600" />
        )}
      </H5>
      {/* actual foldable content */}
      <div className={"mt-2 space-y-2 overflow-x-auto " + (isOpen ? "" : "hidden")}>{children}</div>
    </div>
  )
}

function ShortMessageSummary({ kind, summary }: { kind: string; summary: string }) {
  if (kind == "request") {
    const [method, url] = summary.split(" ")
    return (
      <span className="font-normal">
        <RequestMethodBadge method={method} /> <span className="text-gray-500 font-mono text-xs">{url}</span>
      </span>
    )
  }

  if (kind == "response") {
    const splitSummary = summary.split(" ")
    return (
      <span className="font-normal">
        <ResponseStatusBadge statusCode={parseInt(splitSummary[1])} />
      </span>
    )
  }
}

function MessageHeaders({ id }: { id: string }) {
  const query = useBlobQuery(id)

  if (query && query.isSuccess && query.data !== undefined) {
    return (
      <table className="mb-2 w-full text-xs font-mono">
        <tbody>
          {query.data.content.split("\n").map((line, index) => {
            const s = line.split(":", 2)
            return (
              <tr key={index}>
                <td className="px-2 w-1 text-blue-600 truncate">{s[0]}</td>
                <td className="px-2">{s[1]}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    )
  }
}

function MessageBody({ id }: { id: string }) {
  const query = useBlobQuery(id)

  if (query && query.isSuccess && query.data !== undefined) {
    return (
      <div className="px-2">
        <PrettyBody content={query.data.content} contentType={query.data.contentType} />
      </div>
    )
  }

  return null
}

export function TransactionListPageOnQuerySuccess({
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
            <DetailsCloseButton onClick={() => setSelected(null)} />
          </div>
          <OnQuerySuccess query={detailQuery}>
            {(query) => {
              return (
                <Pane
                  hasDefaultPadding={false}
                  className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm"
                >
                  {(query.data.messages || []).map((message) => (
                    <Foldable
                      title={
                        <>
                          {ucfirst(message.kind)} <ShortMessageSummary kind={message.kind} summary={message.summary} />
                        </>
                      }
                    >
                      <MessageHeaders id={message.headers} />
                      <MessageBody id={message.body} />
                    </Foldable>
                  ))}
                  <Foldable title="Raw" open={false}>
                    <SettingsTable settings={query.data as KeyValueSettings} />
                  </Foldable>
                </Pane>
              )
            }}
          </OnQuerySuccess>
        </aside>
      ) : null}
    </div>
  )
}
