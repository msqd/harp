import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { HeadersTable } from "./HeadersTable"

describe("HeadersTable", () => {
  test("renders without crashing", () => {
    const { container } = render(<HeadersTable headers={{ "Test Header": "Test Value" }} />)
    expect(container).toMatchSnapshot()
  })

  test("renders the correct headers", () => {
    render(<HeadersTable headers={{ "Test Header": "Test Value" }} />)
    const headerElement = screen.getByText(/Test Header/i)
    const valueElement = screen.getByText(/Test Value/i)
    expect(headerElement).toBeInTheDocument()
    expect(valueElement).toBeInTheDocument()
  })
})
