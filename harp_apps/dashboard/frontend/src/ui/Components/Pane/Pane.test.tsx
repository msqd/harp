import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { Pane } from "./Pane"

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
