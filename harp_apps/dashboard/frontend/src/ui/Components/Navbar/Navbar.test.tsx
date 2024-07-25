import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { Navbar } from "./Navbar"

describe("Navbar", () => {
  it("renders correctly", () => {
    const { container } = render(<Navbar />)
    expect(container).toMatchSnapshot()
  })

  it("renders without crashing", () => {
    render(<Navbar />)
    expect(screen.getByRole("navigation")).toBeInTheDocument()
  })

  it("renders the correct number of links", async () => {
    const items = [
      { label: "Home", to: "/" },
      { label: "About", to: "/about" },
      { label: "Contact", to: "/contact" },
    ]
    render(<Navbar items={items} />)

    // Wait for the links to be present in the document
    for (const item of items) {
      const link = await screen.findByText(item.label)
      expect(link).toBeInTheDocument()
    }
  })

  it("correctly identifies the active link", () => {
    const items = [
      { label: "Home", to: "/", exact: true },
      { label: "About", to: "/about" },
      { label: "Contact", to: "/contact" },
    ]
    render(<Navbar items={items} currentPath="/about" />)
    const activeLink = screen.getByText("About")
    expect(activeLink).toHaveClass("border-primary")
  })
})
