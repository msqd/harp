import { useLocation, useNavigate, useSearchParams } from "react-router-dom"

import { apdexScale } from "Components/Badges/constants"
import { useTransactionsFiltersQuery } from "Domain/Transactions"
import { ArrayFilter, Filters, MinMaxFilter } from "Types/filters"
import { Pane } from "ui/Components/Pane"

import { Facet, RangeSliderFacet } from "../Components/Facets"

interface FiltersSidebarProps {
  filters: Filters
}

export function FiltersSidebar({ filters }: FiltersSidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const filtersQuery = useTransactionsFiltersQuery()

  // marks and setup for range slider for tpdex
  const marks = [...apdexScale].map((rating, index) => ({
    value: index * 10,
    label: rating.label,
    className: rating.className,
  }))
  const markValueToThreshold = new Map([...apdexScale].map((rating, index) => [index * 10, rating.threshold]))
  const maxKey = Math.max(...Array.from(markValueToThreshold.keys()))
  const minKey = Math.min(...Array.from(markValueToThreshold.keys()))
  markValueToThreshold.set(maxKey, undefined)
  markValueToThreshold.set(minKey, undefined)

  const thresholdToMarkValue = new Map<number, number>()
  markValueToThreshold.forEach((value, key) => {
    if (value != undefined) {
      thresholdToMarkValue.set(value, key)
    }
  })

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

  const setTpdexValues = (value: MinMaxFilter | undefined) => {
    const maxValue = markValueToThreshold.get(value?.min ?? -1)
    const minValue = markValueToThreshold.get(value?.max ?? -1)

    if (minValue != null) {
      searchParams.set("tpdexmin", minValue.toString())
    } else {
      searchParams.delete("tpdexmin")
    }

    if (maxValue != null) {
      searchParams.set("tpdexmax", maxValue.toString())
    } else {
      searchParams.delete("tpdexmax")
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
          title="Performances Index"
          name="performanceIndex"
          values={{
            min: thresholdToMarkValue.get((filters["tpdex"] as MinMaxFilter)?.max ?? 0),
            max: thresholdToMarkValue.get((filters["tpdex"] as MinMaxFilter)?.min ?? 100),
          }}
          setValues={setTpdexValues}
          marks={marks}
          max={maxKey}
          min={minKey}
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
