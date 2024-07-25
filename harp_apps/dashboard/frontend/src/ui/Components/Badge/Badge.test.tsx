import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { Badge } from "./Badge"

describe("Badge", () => {
  it("renders its children correctly", () => {
    render(<Badge color="green">Hello, world!</Badge>)
    expect(screen.getByText("Hello, world!")).toBeInTheDocument()
  })

  it("renders correctly", () => {
    const { container } = render(<Badge color="green">Test Badge</Badge>)
    expect(container).toMatchSnapshot()
  })
})
