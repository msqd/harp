import { useState } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import { Pane } from "ui/Components/Pane"

import { useTransactionsFiltersQuery } from "Domain/Transactions"
import { Filters, ArrayFilter, MinMaxFilter } from "Types/filters"

import { Facet, RangeSliderFacet } from "../Components/Facets"

interface FiltersSidebarProps {
  filters: Filters
}

export function FiltersSidebar({ filters }: FiltersSidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const filtersQuery = useTransactionsFiltersQuery()
  const [value, setValue] = useState<MinMaxFilter | undefined>({ min: 0, max: 100 })

  const _createSetFilterFor = (name: string) => (value: ArrayFilter) => {
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
          values={filters["endpoint"] as ArrayFilter}
          setValues={setEndpointFilter}
          meta={filtersQuery.data.endpoint.values}
        />
      ) : null}

      {filtersQuery.isSuccess && filtersQuery.data.method ? (
        <Facet
          title="Request Method"
          name="method"
          type="checkboxes"
          values={filters["method"] as ArrayFilter}
          setValues={setMethodFilter}
          meta={filtersQuery.data.method.values}
        />
      ) : null}

      {filtersQuery.isSuccess && filtersQuery.data.status ? (
        <Facet
          title="Response Status"
          name="status"
          type="checkboxes"
          values={filters["status"] as ArrayFilter}
          setValues={setStatusFilter}
          meta={filtersQuery.data.status.values}
        />
      ) : null}

      {filtersQuery.isSuccess && filtersQuery.data.flag ? (
        <Facet
          title="Flags"
          name="flags"
          type="checkboxes"
          values={filters["flag"] as ArrayFilter}
          setValues={setFlagsFilter}
          meta={filtersQuery.data.flag.values}
        />
      ) : null}

      {filtersQuery.isSuccess ? (
        <RangeSliderFacet
          title="Performance Index"
          name="performanceIndex"
          values={value}
          setValues={setValue}
          type={"rangeSlider"}
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
    </Pane>
  )
}
