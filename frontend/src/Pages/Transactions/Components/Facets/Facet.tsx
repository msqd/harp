import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { ChangeEvent, useState } from "react"

import { Filter } from "Types/filters"
import { Checkbox, Radio } from "mkui/Components/FormWidgets"
import { H5 } from "mkui/Components/Typography"

import { FacetLabel } from "./FacetLabel.tsx"

interface FacetProps {
  title: string
  name: string
  type: "checkboxes" | "radios"
  defaultOpen?: boolean
  meta: Array<{ name: string; count?: number }>
  values?: Filter | "*"
  setValues?: (value: Filter) => unknown
}

export function Facet({
  title,
  name,
  values = undefined,
  setValues = undefined,
  meta,
  type,
  defaultOpen = true,
}: FacetProps) {
  const [open, setOpen] = useState(defaultOpen)

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (setValues) {
      const current = new Set(!values || !values.length ? meta.map((x) => x.name) : values)
      if (e.target.checked) {
        current.add(e.target.name)
      } else {
        current.delete(e.target.name)
      }
      setValues(current.size == meta.length || !current.size ? undefined : [...current])
    }
  }

  return (
    <div className="px-4 py-3">
      <fieldset name={name}>
        <H5 as="legend" padding="pt-0" className="flex w-full cursor-pointer" onClick={() => setOpen(!open)}>
          <span className="grow">{title}</span>
          {open ? (
            <ChevronUpIcon className="h-4 w-4 text-gray-600" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 text-gray-600" />
          )}
        </H5>
        <div className={"mt-2 space-y-2 " + (open ? "" : "hidden")}>
          {type === "checkboxes"
            ? meta.map((value) => (
                <Checkbox
                  name={value.name}
                  key={value.name}
                  label={<FacetLabel {...value} />}
                  onChange={onChange}
                  checked={!values || !values.length || values.includes(value.name)}
                />
              ))
            : null}
          {type === "radios"
            ? meta.map((value) => <Radio name={value.name} key={value.name} label={<FacetLabel {...value} />} />)
            : null}
        </div>
      </fieldset>
    </div>
  )
}
