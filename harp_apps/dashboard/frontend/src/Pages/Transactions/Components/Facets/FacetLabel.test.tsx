import { render } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { FacetLabel } from "./FacetLabel"

describe("FacetLabel", () => {
  test("renders correctly", () => {
    const { container } = render(<FacetLabel name={"Facet Name"} />)
    expect(container).toMatchSnapshot()
  })
})
