import { useTransactionsFiltersQuery } from "Domain/Transactions"
import { Filter, Filters } from "Types/filters"

import { Facet } from "./Facets"
import { Pane } from "mkui/Components/Pane"

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
  const setMethodFilter = _createSetFilterFor("method")
  const setStatusFilter = _createSetFilterFor("status")

  return (
    <Pane
      as="aside"
      hasDefaultPadding={false}
      className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm"
    >
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
