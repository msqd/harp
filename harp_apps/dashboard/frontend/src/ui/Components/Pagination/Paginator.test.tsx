import { render, fireEvent } from "@testing-library/react"
import { expect, describe, it, vi } from "vitest"

import { Paginator } from "./Paginator"

describe("Paginator", () => {
  it("renders correctly", () => {
    const { container } = render(<Paginator />)
    expect(container).toMatchSnapshot()
  })

  it("renders without crashing", () => {
    const { getAllByText } = render(<Paginator />)
    const previousButtons = getAllByText("Previous")
    const nextButtons = getAllByText("Next")
    expect(previousButtons.length).toBe(2)
    expect(nextButtons.length).toBe(2)
  })

  describe("when Previous button is clicked", () => {
    it("calls setPage with correct value when previous span clicked", () => {
      const setPage = vi.fn()
      const { getByText } = render(<Paginator current={2} setPage={setPage} />)

      fireEvent.click(getByText("Previous", { selector: "span" }))
      expect(setPage).toHaveBeenCalledWith(1)
    })

    it("calls setPage with correct value when previous anchor clicked", () => {
      const setPage = vi.fn()
      const { getByText } = render(<Paginator current={2} setPage={setPage} />)

      fireEvent.click(getByText("Previous", { selector: "a" }))
      expect(setPage).toHaveBeenCalledWith(1)
    })
  })

  describe("when Next button is clicked", () => {
    it("calls setPage with correct value when next span clicked", () => {
      const setPage = vi.fn()
      const { getByText } = render(<Paginator current={2} setPage={setPage} />)

      fireEvent.click(getByText("Next", { selector: "span" }))
      expect(setPage).toHaveBeenCalledWith(3)
    })

    it("calls setPage with correct value when next anchor clicked", () => {
      const setPage = vi.fn()
      const { getByText } = render(<Paginator current={2} setPage={setPage} />)

      fireEvent.click(getByText("Next", { selector: "a" }))
      expect(setPage).toHaveBeenCalledWith(3)
    })
  })
})
