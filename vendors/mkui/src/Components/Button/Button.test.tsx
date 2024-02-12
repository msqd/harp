import { render, screen } from "@testing-library/react"
import { Button } from "./Button"
import { expect, describe, it } from "vitest"

describe("Button", () => {
  it("renders its children correctly", () => {
    render(<Button>Hello, world!</Button>)
    expect(screen.getByText("Hello, world!")).toBeInTheDocument()
  })

  it("forwards additional props to the underlying button element", () => {
    render(<Button data-testid="my-button">Test</Button>)
    expect(screen.getByTestId("my-button")).toBeInTheDocument()
  })

  it("renders correctly", () => {
    const { container } = render(<Button>Test Button</Button>)
    expect(container).toMatchSnapshot()
  })
})
