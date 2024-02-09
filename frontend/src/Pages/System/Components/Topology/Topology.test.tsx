import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { Topology } from "./Topology"

describe("Topology", () => {
  test("renders correctly with endpoints", () => {
    const endpoints = [
      { name: "Endpoint 1", port: 8080, url: "http://localhost:8080" },
      { name: "Endpoint 2", port: 8081, url: "http://localhost:8081" },
    ]

    render(<Topology endpoints={endpoints} />)

    // Check that the Localhost and HARP texts are rendered
    expect(screen.getByText("Localhost")).toBeInTheDocument()
    expect(screen.getByText("HARP")).toBeInTheDocument()

    // Check that the endpoint names are rendered
    endpoints.forEach((endpoint) => {
      expect(screen.getByText(endpoint.name)).toBeInTheDocument()
    })
  })

  test("does not render without endpoints", () => {
    const { container } = render(<Topology />)
    console.log(container)
    expect(container.firstChild).toBeNull()
  })
})
