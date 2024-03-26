import { render } from "@testing-library/react"
import { Pane } from "./Pane"
import { expect, describe, it } from "vitest"

describe("Pane", () => {
  it("renders correctly", () => {
    const { container } = render(<Pane />)
    expect(container).toMatchSnapshot()
  })

  it("renders without crashing", () => {
    const { container } = render(<Pane />)
    expect(container.firstChild).toBeTruthy()
  })
})
