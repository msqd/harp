import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { SearchBar } from "./SearchBar"

describe("SearchBar", () => {
  it("renders correctly", () => {
    const { container } = render(<SearchBar />)
    expect(container).toMatchSnapshot()
  })
})
