import { ButtonGroup as ButtonGroupComponent } from "./ButtonGroup"
import { useState } from "react"

export const ButtonGroup = () => {
  const [current, setCurrent] = useState("1")

  const setCurrentButton = (current: string) => {
    setCurrent(current)
  }
  const buttonProps = [
    { key: "1", title: "24h" },
    { key: "2", title: "7d" },
    { key: "3", title: "1m" },
  ]
  return (
    <div className="flex flex-col space-y-4">
      <ButtonGroupComponent buttonProps={buttonProps} current={current} setCurrent={setCurrentButton} />
    </div>
  )
}
