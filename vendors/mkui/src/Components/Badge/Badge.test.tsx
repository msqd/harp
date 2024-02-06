import { render, screen } from "@testing-library/react"
import { Badge } from "./Badge"

describe("Badge", () => {
  it("renders its children correctly", () => {
    render(<Badge color="green">Hello, world!</Badge>)
    expect(screen.getByText("Hello, world!")).toBeInTheDocument()
  })
})
