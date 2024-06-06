import { useCallback, useEffect } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { useTransactionsFiltersQuery } from "Domain/Transactions"
import { Filter, Filters } from "Types/filters"
import { Pane } from "ui/Components/Pane"

import { Facet } from "../Components/Facets"

const ratings = [
  { name: "A++" },
  { name: "A+" },
  { name: "A" },
  { name: "B" },
  { name: "C" },
  { name: "D" },
  { name: "E" },
  { name: "F" },
]

interface FiltersSidebarProps {
  filters: Filters
  setFilters: (filters: Filters) => unknown
}

export function FiltersSidebar({ filters, setFilters }: FiltersSidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()

  const filtersQuery = useTransactionsFiltersQuery()

  const _createSetFilterFor = (name: string) =>
    useCallback(
      (value: Filter) => {
        setFilters({ ...filters, [name]: value })
      },
      [name],
    )

  const setEndpointFilter = _createSetFilterFor("endpoint")
  const setMethodFilter = _createSetFilterFor("method")
  const setStatusFilter = _createSetFilterFor("status")
  const setFlagsFilter = _createSetFilterFor("flag")

  // Set filters from query parameters
  useEffect(() => {
    const filtersMap = {
      endpoint: setEndpointFilter,
      method: setMethodFilter,
      status: setStatusFilter,
      flag: setFlagsFilter,
    }
    const queryParams = new URLSearchParams(location.search)
    const updateFilter = (name: string, setFunction: (value: Filter) => void) => {
      const values = queryParams.getAll(name)
      if (values.length) {
        setFunction(values)
      }
    }

    for (const [name, setFunction] of Object.entries(filtersMap)) {
      updateFilter(name, setFunction)
    }
  }, [location.search, setEndpointFilter, setMethodFilter, setStatusFilter, setFlagsFilter])

  // Update query parameters from filters
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search)

    const updateQueryParams = (filterName: string) => {
      if (!filters[filterName] || !filters[filterName]?.length) {
        queryParams.delete(filterName)
      } else {
        // Delete existing query parameters for the filter
        queryParams.delete(filterName)

        // Append new query parameters for the filter
        filters[filterName]?.forEach((value) => queryParams.append(filterName, String(value)))
      }
    }

    // Update query parameters for each filter
    Object.keys(filters).forEach(updateQueryParams)

    navigate({
      pathname: location.pathname,
      search: queryParams.toString(),
    })
  }, [filters, location.pathname, location.search, navigate])

  return (
    <Pane hasDefaultPadding={false} className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm">
      {/* TODO implement search
      <input className="h-12 w-full border-0 bg-transparent px-4 focus:ring-0" placeholder="Search..." />
     */}

      {filtersQuery.isSuccess && filtersQuery.data.endpoint ? (
        <Facet
          title="Endpoint"
          name="endpoint"
          type="checkboxes"
          values={filters["endpoint"]}
          setValues={setEndpointFilter}
          meta={filtersQuery.data.endpoint.values}
        />
      ) : null}

      {filtersQuery.isSuccess && filtersQuery.data.method ? (
        <Facet
          title="Request Method"
          name="method"
          type="checkboxes"
          values={filters["method"]}
          setValues={setMethodFilter}
          meta={filtersQuery.data.method.values}
        />
      ) : null}

      {filtersQuery.isSuccess && filtersQuery.data.status ? (
        <Facet
          title="Response Status"
          name="status"
          type="checkboxes"
          values={filters["status"]}
          setValues={setStatusFilter}
          meta={filtersQuery.data.status.values}
        />
      ) : null}

      {filtersQuery.isSuccess && filtersQuery.data.flag ? (
        <Facet
          title="Flags"
          name="flags"
          type="checkboxes"
          values={filters["flag"]}
          setValues={setFlagsFilter}
          meta={filtersQuery.data.flag.values}
        />
      ) : null}

      {/* TODO implement */}
      {filtersQuery.isSuccess && filtersQuery.data.period ? (
        <Facet
          title="Period"
          name="period"
          meta={[{ name: "Last 24 hours" }, { name: "Last 7 days" }, { name: "Last 15 days" }]}
          type="radios"
        />
      ) : null}

      {/* TODO implement */}
      {filtersQuery.isSuccess && filtersQuery.data.apdex ? (
        <Facet title="Performance Index" name="tpdex" meta={ratings} type="checkboxes" defaultOpen={false} />
      ) : null}
    </Pane>
  )
}
