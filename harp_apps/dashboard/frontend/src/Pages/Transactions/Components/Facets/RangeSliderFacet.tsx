import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { useState } from "react"

import { MinMaxFilter } from "Types/filters"
import { RangeSlider } from "ui/Components/Slider/RangeSlider.tsx"
import { H5 } from "ui/Components/Typography"

import { FacetInnerLightButton } from "./FacetInnerLightButton.tsx"

interface RangeSliderFacetProps {
  title: string
  name: string
  type: "rangeSlider"
  defaultOpen?: boolean
  values?: MinMaxFilter
  setValues: (value?: MinMaxFilter) => void
}

/**
 * Facet component, renders a facet (group of values that can filter a given field) with checkboxes or radios.
 *
 * Radios for single selection, checkboxes for multiple selection. La base.
 */
export function RangeSliderFacet({
  title,
  name,
  values = undefined,
  setValues,
  defaultOpen = true,
}: RangeSliderFacetProps) {
  /**
   * Should this facet be open (aka, unfolded)? Default value can be passed as a prop, then the component will manage
   * the open state.
   */
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="px-4 py-3">
      <fieldset name={name}>
        <H5 as="legend" padding="pt-0" className="flex w-full cursor-pointer" onClick={() => setOpen(!open)}>
          <span className="grow">
            {title}
            {values ? <FacetInnerLightButton label="reset" handler={() => setValues(undefined)} /> : null}
          </span>
          {open ? (
            <ChevronUpIcon className="h-4 w-4 text-gray-600" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 text-gray-600" />
          )}
        </H5>
        <div className={"mt-2 space-y-2 " + (open ? "" : "hidden")}>
          <RangeSlider min={0} max={100} defaultValue={values} onPointerUp={setValues} />
        </div>
      </fieldset>
    </div>
  )
}
