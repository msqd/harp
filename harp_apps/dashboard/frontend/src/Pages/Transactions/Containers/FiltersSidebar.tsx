import { useLocation, useNavigate, useSearchParams } from "react-router-dom"

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
}

export function FiltersSidebar({ filters }: FiltersSidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const filtersQuery = useTransactionsFiltersQuery()

  const _createSetFilterFor = (name: string) => (value: Filter) => {
    searchParams.delete(name)
    if (value) {
      value.forEach((v) => {
        if (v) {
          searchParams.append(name, v.toString())
        }
      })
    }

    navigate(
      {
        pathname: location.pathname,
        search: searchParams.toString(),
      },
      { replace: false },
    )
  }

  const setEndpointFilter = _createSetFilterFor("endpoint")
  const setMethodFilter = _createSetFilterFor("method")
  const setStatusFilter = _createSetFilterFor("status")
  const setFlagsFilter = _createSetFilterFor("flag")

  return (
    <Pane hasDefaultPadding={false} className="divide-y divide-gray-100 overflow-hidden text-gray-900 sm:text-sm">
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
