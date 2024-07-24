import { useState } from "react"

import { RangeSlider } from "./RangeSlider"

type SliderValue = { min?: number; max?: number }

const marks = [
  {
    value: 0,
    label: "0",
  },
  {
    value: 10,
    label: "10",
  },
  {
    value: 20,
    label: "20",
  },
  {
    value: 30,
    label: "30",
  },
  {
    value: 40,
    label: "40",
  },
  {
    value: 50,
    label: "50",
  },
  {
    value: 60,
    label: "60",
  },
  {
    value: 70,
    label: "70",
  },
  {
    value: 80,
    label: "80",
  },
  {
    value: 90,
    label: "90",
  },
  {
    value: 100,
    label: "100",
  },
]
export const Default = () => {
  const [value, setValue] = useState<SliderValue>({ min: 10, max: 50 })

  return (
    <>
      <RangeSlider
        min={0}
        max={100}
        step={10}
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
