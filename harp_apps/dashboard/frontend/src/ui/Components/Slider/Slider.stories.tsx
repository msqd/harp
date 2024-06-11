import { useState } from "react"
import { RangeSlider } from "./Slider"

export const Default = () => {
  const [value, setValue] = useState({ min: 0, max: 100 })

  return (
    <>
      <RangeSlider min={0} max={100} step={1} value={value} onChange={setValue} />
      <p>
        The min value is: <span>{value.min}</span>
      </p>
      <p>
        The max value is: <span>{value.max}</span>
      </p>
    </>
  )
}
