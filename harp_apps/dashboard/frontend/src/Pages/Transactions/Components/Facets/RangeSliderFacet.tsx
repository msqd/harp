import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { useState } from "react"

import { MinMaxFilter } from "Types/filters"
import { RangeSlider, Mark } from "ui/Components/Slider/RangeSlider.tsx"
import { H5 } from "ui/Components/Typography"

import { FacetInnerLightButton } from "./FacetInnerLightButton.tsx"

interface RangeSliderFacetProps {
  title: string
  name: string
  type: "rangeSlider"
  defaultOpen?: boolean
  values?: MinMaxFilter
  setValues: (value?: MinMaxFilter) => void
  marks?: Mark[]
  min?: number
  max?: number
}

export function RangeSliderFacet({
  title,
  name,
  values = undefined,
  setValues,
  defaultOpen = true,
  marks,
  min,
  max,
}: RangeSliderFacetProps) {
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
          <RangeSlider
            min={min}
            max={max}
            step={10}
            defaultValue={values}
            onPointerUp={setValues}
            marks={marks}
            thumbSize="8px"
          />
        </div>
      </fieldset>
    </div>
  )
}
