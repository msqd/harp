import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { DevelopmentOnlyWarning } from "./DevelopmentOnlyWarning"

const settings = [
  { name: "storage.url", message: "SQLite storage is meant for development: use PostgreSQL in production." },
  { name: "HARP_DEBUG", message: "Debug mode is on: unset HARP_DEBUG in production." },
]

const sign = () => screen.getByRole("button", { name: /development-only settings/i })

describe("DevelopmentOnlyWarning", () => {
  it("renders nothing when no setting is development-only", () => {
    const { container } = render(<DevelopmentOnlyWarning settings={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it("shows a warning sign that hides the list until it is clicked", () => {
    render(<DevelopmentOnlyWarning settings={settings} />)
    expect(sign()).toBeInTheDocument()
    expect(screen.queryByText("storage.url")).not.toBeInTheDocument()
  })

  it("lists each setting and what to use instead once opened", () => {
    render(<DevelopmentOnlyWarning settings={settings} />)
    fireEvent.click(sign())

    expect(screen.getByText("storage.url")).toBeInTheDocument()
    expect(screen.getByText(/use PostgreSQL in production/)).toBeInTheDocument()
    expect(screen.getByText("HARP_DEBUG")).toBeInTheDocument()
    expect(screen.getByText(/unset HARP_DEBUG/)).toBeInTheDocument()
  })

  it("renders correctly when opened", () => {
    const { baseElement } = render(<DevelopmentOnlyWarning settings={settings} />)
    fireEvent.click(sign())
    expect(baseElement).toMatchSnapshot()
  })
})
