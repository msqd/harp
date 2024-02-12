import { render, fireEvent, screen } from "@testing-library/react"
import { ButtonGroup } from "./ButtonGroup"
import { expect, describe, it, vi } from "vitest"

describe("ButtonGroup", () => {
  const buttonProps = [
    { key: "1", title: "Button 1" },
    { key: "2", title: "Button 2" },
    { key: "3", title: "Button 3" },
  ]

  it("renders without crashing", () => {
    render(<ButtonGroup buttonProps={buttonProps} current="1" setCurrent={() => {}} />)
  })

  it("renders the correct number of buttons", () => {
    const { getAllByRole } = render(<ButtonGroup buttonProps={buttonProps} current="1" setCurrent={() => {}} />)
    const buttons = getAllByRole("button")
    expect(buttons.length).toBe(buttonProps.length)
  })

  it("calls setCurrent with the correct key when a button is clicked", () => {
    const setCurrent = vi.fn()
    const { getByText } = render(<ButtonGroup buttonProps={buttonProps} current="1" setCurrent={setCurrent} />)
    fireEvent.click(getByText("Button 3"))
    expect(setCurrent).toHaveBeenCalledWith("3")
  })

  it("renders correctly", () => {
    const { container } = render(<ButtonGroup buttonProps={buttonProps} current="1" setCurrent={() => {}} />)
    expect(container).toMatchSnapshot()
  })
})
