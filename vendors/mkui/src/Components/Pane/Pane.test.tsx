import { render } from "@testing-library/react"
import { Pane } from "./Pane"

describe("Pane", () => {
  it("renders without crashing", () => {
    const { container } = render(<Pane />)
    expect(container.firstChild).toBeTruthy()
  })
})
