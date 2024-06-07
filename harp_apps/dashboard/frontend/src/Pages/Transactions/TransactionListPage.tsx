import { isEqual } from "lodash"
import { useCallback, useEffect, useRef } from "react"
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

  const filters = defaultFilters(searchParams)

  // const filters = defaultFilters(searchParams)
  const cursor = searchParams.get("cursor")
  const search = searchParams.get("search")
  const page = searchParams.get("page") ? parseInt(searchParams.get("page")!) : 1

  const query = useTransactionsListQuery({ filters, page, cursor, search })

  // Keep refs of filters and search to reset page when a change is detected
  const prevSearchRef = useRef<string | null>()
  const prevFiltersRef = useRef<Filters>({})

  const updateQueryParam = useCallback(
    (paramName: string, paramValue: string | undefined) => {
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
    },
    [location.pathname, navigate, searchParams],
  )

  // update cursor
  useEffect(() => {
    if (page == 1 && query.isSuccess && query.data.items.length && query.data.items[0].id) {
      if (cursor != query.data.items[0].id) {
        updateQueryParam("cursor", query.data.items[0].id)
      }
    }
  }, [page, navigate, query, cursor, searchParams, location.pathname, updateQueryParam])

  // go back to page 1
  useEffect(() => {
    if (!isEqual(filters, prevFiltersRef.current) || search !== prevSearchRef.current) {
      updateQueryParam("page", "1")
      prevFiltersRef.current = filters
      prevSearchRef.current = search
    }
  }, [filters, search, updateQueryParam])

  useEffect(() => {
    // This code will run whenever the location changes
    console.log("Location changed:", location)
  }, [location])

  return (
    <Page
      title={
        <PageTitle title="Transactions" description="Explore transactions that went through the proxy">
          <div className="flex flex-col ml-24 w-full items-end lg:items-start justify-end lg:justify-between lg:flex-row lg:mt-12">
            <SearchBar
              placeHolder="Search transactions"
              setSearch={(search) => updateQueryParam("search", search)}
              className="w-96 order-last lg:order-first pr-6"
              search={search}
            />
            {query.isSuccess ? (
              <OptionalPaginator
                current={page}
                setPage={(page) => updateQueryParam("page", page.toString())}
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
        {(query) => <TransactionListOnQuerySuccess query={query} filters={filters} />}
      </OnQuerySuccess>
    </Page>
  )
}
