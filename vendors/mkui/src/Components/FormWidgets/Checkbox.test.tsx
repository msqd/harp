import { render, screen, fireEvent } from "@testing-library/react"
import { Checkbox } from "./Checkbox"
import { expect, describe, it } from "vitest"

describe("Checkbox", () => {
  it("renders correctly", () => {
    const { container } = render(<Checkbox name="test-checkbox" />)
    expect(container).toMatchSnapshot()
  })

  it("renders the checkbox input and label", () => {
    render(<Checkbox name="test-checkbox" label="Test Checkbox" />)

    const checkboxInput = screen.getByRole("checkbox")
    expect(checkboxInput).toBeInTheDocument()
    expect(checkboxInput).toHaveAttribute("name", "test-checkbox")

    const label = screen.getByText("Test Checkbox")
    expect(label).toBeInTheDocument()
  })

  it("uses the name as label when label prop is not provided", () => {
    render(<Checkbox name="test-checkbox" />)

    const label = screen.getByText("test-checkbox")
    expect(label).toBeInTheDocument()
  })

  it("passes checked prop to the input element", () => {
    render(<Checkbox name="test-checkbox" checked={true} onChange={() => {}} />)

    const checkboxInput = screen.getByRole("checkbox")
    expect(checkboxInput).toBeChecked()
  })

  it("passes containerProps to the container div", () => {
    render(<Checkbox name="test-checkbox" containerProps={{ "data-testid": "container" }} />)

    const container = screen.getByTestId("container")
    expect(container).toBeInTheDocument()
  })

  it("passes labelProps to the label element", () => {
    render(<Checkbox name="test-checkbox" labelProps={{ "data-testid": "label" }} />)

    const label = screen.getByTestId("label")
    expect(label).toBeInTheDocument()
  })

  it("handles container click", () => {
    render(<Checkbox name="test-checkbox" />)

    const container = screen.getByRole("checkbox").parentElement?.parentElement
    if (container) {
      fireEvent.click(container)
    }

    const checkboxInput = screen.getByRole("checkbox")
    expect(checkboxInput).toBeChecked()
  })
})
