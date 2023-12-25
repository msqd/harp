import { useCallback, useMemo } from "react"
import tw, { styled } from "twin.macro"

import { useTransactionsFiltersQuery } from "Domain/Transactions"
import { Filter, Filters, FilterValue } from "Types/filters"

import { Facet } from "./Facets/Facet.tsx"

const StyledSidebar = styled.aside`
  ${tw`max-w-full w-full divide-y divide-gray-100 overflow-hidden bg-white shadow-sm ring-1 ring-black ring-opacity-5`}
  ${tw`text-gray-900 sm:text-sm`}
`
const methods = [{ name: "GET" }, { name: "POST" }, { name: "PUT" }, { name: "DELETE" }]
const statuses = [{ name: "2xx" }, { name: "3xx" }, { name: "4xx" }, { name: "5xx" }]
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
  const filtersQuery = useTransactionsFiltersQuery()

  const _createSetFilterFor = (name: string) => (value: Filter) => {
    setFilters({ ...filters, [name]: value })
  }

  const setEndpointFilter = _createSetFilterFor("endpoint")

  return (
    <StyledSidebar>
      <input className="h-12 w-full border-0 bg-transparent px-4 focus:ring-0" placeholder="Search..." />
      {filtersQuery.isSuccess && filtersQuery.data.endpoint ? (
        <Facet
          title="Endpoint"
          name="endpoint"
          type="checkboxes"
          values={filters["endpoint"] ?? "*"}
          setValues={setEndpointFilter}
          meta={filtersQuery.data.endpoint.values}
        />
      ) : null}
      <Facet title="Request Method" name="method" meta={methods} type="checkboxes" />
      <Facet title="Response Status" name="status" meta={statuses} type="checkboxes" />
      <Facet
        title="Period"
        name="period"
        meta={[{ name: "Last 24 hours" }, { name: "Last 7 days" }, { name: "Last 15 days" }]}
        type="radios"
      />
      <Facet title="Performance Index" name="tpdex" meta={ratings} type="checkboxes" defaultOpen={false} />
    </StyledSidebar>
  )
}
