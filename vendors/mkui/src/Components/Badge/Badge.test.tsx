import { render, screen } from "@testing-library/react"
import { Badge } from "./Badge"

describe("Badge", () => {
  it("renders its children correctly", () => {
    render(<Badge color="green">Hello, world!</Badge>)
    expect(screen.getByText("Hello, world!")).toBeInTheDocument()
  })

  it("renders correctly", () => {
    const { asFragment } = render(<Badge color="green">Test Badge</Badge>)
    expect(asFragment()).toMatchSnapshot()
  })
})
