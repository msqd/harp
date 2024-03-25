import { render } from "@testing-library/react"
import { describe, expect, test, vi } from "vitest"

import { FacetInnerLightButton } from "./FacetInnerLightButton"

describe("FacetInnerLightButton", () => {
  test("renders correctly", () => {
    const handler = vi.fn()
    const { container } = render(<FacetInnerLightButton label="Test Label" handler={handler} />)
    expect(container).toMatchSnapshot()
  })
})
