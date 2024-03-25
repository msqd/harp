import { render, screen } from "@testing-library/react"
import { Radio } from "./Radio"
import { expect, describe, it } from "vitest"

describe("Radio", () => {
  it("renders correctly", () => {
    const { container } = render(<Radio name="test-radio" />)
    expect(container).toMatchSnapshot()
  })

  it("renders the radio input and label", () => {
    render(<Radio name="test-radio" label="Test Radio" />)

    const radioInput = screen.getByRole("radio")
    expect(radioInput).toBeInTheDocument()
    expect(radioInput).toHaveAttribute("name", "push-notifications")

    const label = screen.getByText("Test Radio")
    expect(label).toBeInTheDocument()
  })

  it("uses the name as label when label prop is not provided", () => {
    render(<Radio name="test-radio" />)

    const label = screen.getByText("test-radio")
    expect(label).toBeInTheDocument()
  })

  it("passes inputProps to the input element", () => {
    render(<Radio name="test-radio" inputProps={{ checked: true, onChange: () => {} }} />)

    const radioInput = screen.getByRole("radio")
    expect(radioInput).toBeChecked()
  })

  it("passes containerProps to the container div", () => {
    render(<Radio name="test-radio" containerProps={{ "data-testid": "container" }} />)

    const container = screen.getByTestId("container")
    expect(container).toBeInTheDocument()
  })
})
