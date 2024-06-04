import { isEqual } from "lodash"
import { useEffect, useMemo, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { Page } from "Components/Page"
import { PageTitle } from "Components/Page/PageTitle.tsx"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Filters } from "Types/filters"
import { SearchBar } from "ui/Components/SearchBar/SearchBar"

import { OptionalPaginator } from "./Components/OptionalPaginator.tsx"
import { TransactionListOnQuerySuccess } from "./TransactionListOnQuerySuccess.tsx"

export function TransactionListPage() {
  const location = useLocation()

  const navigate = useNavigate()

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search])

  const [filters, setFilters] = useState<Filters>({})

  const [page, setPage] = useState(Number(queryParams.get("page")) || 1)
  const [cursor, setCursor] = useState<string | undefined>(queryParams.get("cursor") || undefined)
  const [search, setSearch] = useState<string | undefined>(queryParams.get("search") || undefined)
  const query = useTransactionsListQuery({ filters, page, cursor, search })

  useEffect(() => {
    const queryParamsToUpdate = { page: page.toString(), cursor: cursor, search: search }
    const updateQueryParam = (paramName: string, paramValue: string | undefined) => {
      if (paramValue) {
        queryParams.set(paramName, paramValue)
      } else {
        queryParams.delete(paramName)
      }

      navigate({
        pathname: location.pathname,
        search: queryParams.toString(),
      })
    }

    for (const [key, value] of Object.entries(queryParamsToUpdate)) {
      updateQueryParam(key, value)
    }
  }, [location.pathname, navigate, queryParams, search, cursor, page])

  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length) {
      setCursor(query.data.items[0].id)
    }
  }, [page, query])

  const prevFiltersRef = useRef<Filters>({})

  useEffect(() => {
    console.log("Filters", prevFiltersRef.current)
    if (!isEqual(filters, prevFiltersRef.current)) {
      console.log("Filters changed")
      setPage((prevPage) => (prevPage > 1 ? 1 : prevPage))
      prevFiltersRef.current = filters
    }
  }, [filters])

  return (
    <Page
      title={
        <PageTitle title="Transactions" description="Explore transactions that went through the proxy">
          <div className="flex flex-col ml-24 w-full items-end lg:items-start justify-end lg:justify-between lg:flex-row lg:mt-12">
            <SearchBar
              placeHolder="Search transactions"
              setSearch={setSearch}
              className="w-96 order-last lg:order-first pr-6"
              search={search}
            />
            {query.isSuccess ? (
              <OptionalPaginator
                current={page}
                setPage={setPage}
                total={query.data.total}
                pages={query.data.pages}
                perPage={query.data.perPage}
              />
            ) : (
              <div className="block order-first lg:order-last"></div>
            )}
          </div>
        </PageTitle>
      }
    >
      <OnQuerySuccess query={query}>
        {(query) => <TransactionListOnQuerySuccess query={query} filters={filters} setFilters={setFilters} />}
      </OnQuerySuccess>
    </Page>
  )
}
