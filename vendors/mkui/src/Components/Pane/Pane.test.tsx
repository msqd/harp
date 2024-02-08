import { render } from "@testing-library/react"
import { Pane } from "./Pane"

describe("Pane", () => {
  it("renders correctly", () => {
    const { asFragment } = render(<Pane />)
    expect(asFragment()).toMatchSnapshot()
  })

  it("renders without crashing", () => {
    const { container } = render(<Pane />)
    expect(container.firstChild).toBeTruthy()
  })
})
