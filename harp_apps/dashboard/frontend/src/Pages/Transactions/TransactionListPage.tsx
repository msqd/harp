import { isEqual } from "lodash"
import { useCallback, useEffect, useRef, useState } from "react"
import { Helmet } from "react-helmet"
import { useQueryClient } from "react-query"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"

import { OnQuerySuccess } from "Components"
import { Page } from "Components/Page"
import { PageTitle } from "Components/Page/PageTitle.tsx"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Filters } from "Types/filters"
import { SearchBar } from "ui/Components/SearchBar/SearchBar"
import { H1 } from "ui/Components/Typography"

import { RefreshButton } from "./Components/Buttons.tsx"
import { TransactionsDataTableProps } from "./Components/List/TransactionDataTable.tsx"
import { OptionalPaginator } from "./Components/OptionalPaginator.tsx"
import { TransactionListOnQuerySuccess } from "./TransactionListOnQuerySuccess.tsx"

interface TransactionListPageProps {
  TransactionDataTable: React.FC<TransactionsDataTableProps>
}

export default function TransactionListPage({ TransactionDataTable }: TransactionListPageProps) {
  const location = useLocation()

  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [searchParams] = useSearchParams()

  const defaultFilters = (searchParams: URLSearchParams): Filters => {
    const filtersMap: Partial<Filters> = {}
    const filtersNames = ["endpoint", "method", "status", "flag"]

    for (const name of filtersNames) {
      const values = searchParams.getAll(name)
      if (values.length > 0) {
        filtersMap[name] = values
      }
    }

    // tpdex
    const tpdexMin = searchParams.get("tpdexmin")
    const tpdexMax = searchParams.get("tpdexmax")
    filtersMap["tpdex"] = {
      min: tpdexMin ? parseFloat(tpdexMin) : undefined,
      max: tpdexMax ? parseFloat(tpdexMax) : undefined,
    }

    return filtersMap
  }

  const filters = defaultFilters(searchParams)
  const cursorFromSearchParams = searchParams.get("cursor")
  const [cursor, setCursor] = useState<string>(cursorFromSearchParams || "")
  const search = searchParams.get("search")
  const page = searchParams.get("page") ? parseInt(searchParams.get("page")!) : 1

  const query = useTransactionsListQuery({ filters, page, cursor, search })

  // Keep refs of filters and search to reset page when a change is detected
  const prevSearchRef = useRef<string | null>(null)
  const prevFiltersRef = useRef<Filters>({})

  const updateQueryParams = useCallback(
    (params: Record<string, string | undefined>) => {
      Object.entries(params).forEach(([paramName, paramValue]) => {
        if (paramValue) {
          searchParams.set(paramName, paramValue)
        } else {
          searchParams.delete(paramName)
        }
      })

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
      setCursor(query.data.items[0].id)
    }
  }, [page, query.data?.items, query.isSuccess])

  // go back to page 1
  useEffect(() => {
    if (!isEqual(filters, prevFiltersRef.current) || search !== prevSearchRef.current) {
      prevFiltersRef.current = filters
      prevSearchRef.current = search
      if (page !== 1) {
        updateQueryParams({ page: undefined, cursor: undefined })
      }
    }
  }, [filters, page, search, updateQueryParams])

  return (
    <Page
      title={
        <PageTitle
          title={
            <H1 className="flex">
              Transactions
              <RefreshButton onClick={() => void queryClient.invalidateQueries(["transactions"])} />
            </H1>
          }
          description="Explore transactions that went through the proxy"
        >
          <div className="flex flex-col ml-24 w-full items-end lg:items-start justify-end lg:justify-between lg:flex-row mt-8">
            <SearchBar
              placeHolder="Search transactions"
              setSearch={(search) => updateQueryParams({ search: search })}
              className="w-96 order-last lg:order-first pr-6"
              search={search}
            />
            {query.isSuccess ? (
              <div className="flex flex-col items-end">
                <OptionalPaginator
                  current={page}
                  setPage={(page) => {
                    if (page > 1) {
                      updateQueryParams({ page: page.toString(), cursor: cursor })
                    } else {
                      updateQueryParams({ page: undefined, cursor: undefined })
                    }
                  }}
                  total={query.data.total}
                  pages={query.data.pages}
                  perPage={query.data.perPage}
                />
                <div className="px-4 sm:px-6 text-sm text-secondary-400">
                  Showing {query.data.items.length} of {query.data.total} transactions
                </div>
              </div>
            ) : (
              <div className="block order-first lg:order-last"></div>
            )}
          </div>
        </PageTitle>
      }
    >
      <Helmet>
        <title>Transactions | Harp</title>
        <meta name="description" content="Transactions list page" />
      </Helmet>

      <OnQuerySuccess query={query}>
        {(query) => (
          <TransactionListOnQuerySuccess query={query} filters={filters} TransactionDataTable={TransactionDataTable} />
        )}
      </OnQuerySuccess>
    </Page>
  )
}
