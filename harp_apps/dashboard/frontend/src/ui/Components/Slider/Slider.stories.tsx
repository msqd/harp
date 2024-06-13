import { useState } from "react"

import { RangeSlider } from "./RangeSlider"
type SliderValue = { min?: number; max?: number }

const marks = [
  {
    value: 0,
    label: "0",
  },
  {
    value: 50,
    label: "50",
  },
  {
    value: 100,
    label: "100",
  },
]
export const Default = () => {
  const [value, setValue] = useState<SliderValue>({ min: 33, max: 77 })

  return (
    <>
      <RangeSlider
        min={0}
        max={100}
        step={1}
        defaultValue={{ min: value.min, max: value.max }}
        onPointerUp={setValue}
        marks={marks}
      />
      <p>
        The min value is: <span>{value.min}</span>
      </p>
      <p>
        The max value is: <span>{value.max}</span>
      </p>
    </>
  )
}
