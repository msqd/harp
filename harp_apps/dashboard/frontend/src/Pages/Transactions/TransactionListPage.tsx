import { isEqual } from "lodash"
import { useEffect, useRef, useState } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"

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

  const [searchParams] = useSearchParams()

  const defaultFilters = (searchParams: URLSearchParams): Filters => {
    const filtersMap: Partial<Filters> = {
      endpoint: [],
      method: [],
      status: [],
      flag: [],
    }

    for (const name of Object.keys(filtersMap)) {
      const values = searchParams.getAll(name)
      if (values.length > 0) {
        filtersMap[name] = values
      }
    }

    return filtersMap
  }

  const [filters, setFilters] = useState<Filters>(defaultFilters(searchParams))

  const [page, setPage] = useState(Number(searchParams.get("page")) || 1)
  const [cursor, setCursor] = useState<string | undefined>(searchParams.get("cursor") || undefined)
  const [search, setSearch] = useState<string | undefined>(searchParams.get("search") || undefined)
  const query = useTransactionsListQuery({ filters, page, cursor, search })

  // Keep refs of filters and search to reset page when a change is detected
  const prevSearchRef = useRef<string | undefined>()
  const prevFiltersRef = useRef<Filters>({})

  // update search and page query params
  useEffect(() => {
    const queryParamsToUpdate = { page: page.toString(), search: search }
    const updateQueryParam = (paramName: string, paramValue: string | undefined) => {
      if (paramValue) {
        searchParams.set(paramName, paramValue)
      } else {
        searchParams.delete(paramName)
      }

      navigate({
        pathname: location.pathname,
        search: searchParams.toString(),
      })
    }

    for (const [key, value] of Object.entries(queryParamsToUpdate)) {
      updateQueryParam(key, value)
    }
  }, [location.pathname, navigate, search, page, searchParams])

  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length && query.data.items[0].id) {
      if (cursor != query.data.items[0].id) {
        setCursor(query.data.items[0].id)
        searchParams.set("cursor", query.data.items[0].id)
        navigate({
          pathname: "/transactions",
          search: searchParams.toString(),
        })
      }
    }
  }, [page, navigate, query, cursor, searchParams])

  // go back to page 1
  useEffect(() => {
    if (!isEqual(filters, prevFiltersRef.current)) {
      setPage((prevPage) => (prevPage > 1 ? 1 : prevPage))
      prevFiltersRef.current = filters
    }
  }, [filters])

  useEffect(() => {
    if (search !== prevSearchRef.current) {
      setPage((prevPage) => (prevPage > 1 ? 1 : prevPage))
      prevSearchRef.current = search
    }
  }, [search])

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
