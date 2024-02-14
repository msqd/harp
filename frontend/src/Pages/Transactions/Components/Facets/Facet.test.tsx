import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { Facet } from "./Facet"

describe("Facet", () => {
  test("renders without crashing", () => {
    const { container } = render(<Facet title="Test Title" name="test-name" type="checkboxes" meta={[]} />)
    expect(container).toMatchSnapshot()
  })
})
