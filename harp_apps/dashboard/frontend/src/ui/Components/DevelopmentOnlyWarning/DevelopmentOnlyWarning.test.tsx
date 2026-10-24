import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { DevelopmentOnlyWarning } from "./DevelopmentOnlyWarning"

const settings = [
  { name: "storage.url", message: "SQLite storage is meant for development: use PostgreSQL in production." },
  { name: "HARP_DEBUG", message: "Debug mode is on: unset HARP_DEBUG in production." },
]
const documentationUrl = "https://docs.example.test/user/"

const renderPill = (list = settings) =>
  render(<DevelopmentOnlyWarning settings={list} documentationUrl={documentationUrl} />)
const pill = () => screen.getByRole("button", { name: /development-only settings in use/i })

describe("DevelopmentOnlyWarning", () => {
  it("renders nothing when no setting is development-only", () => {
    const { container } = renderPill([])
    expect(container).toBeEmptyDOMElement()
  })

  it("shows a short label and the count, and names the full text for assistive technology", () => {
    renderPill()
    expect(pill()).toHaveTextContent("Dev2")
    expect(pill()).toHaveAccessibleName("Development-only settings in use: 2")
    expect(pill()).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByText("storage.url")).not.toBeInTheDocument()
  })

  it("lists each setting and the documentation link once opened", () => {
    renderPill()
    fireEvent.click(pill())

    expect(pill()).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText("storage.url")).toBeInTheDocument()
    expect(screen.getByText(/use PostgreSQL in production/)).toBeInTheDocument()
    expect(screen.getByText("HARP_DEBUG")).toBeInTheDocument()
    expect(screen.getByText(/unset HARP_DEBUG/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /going to production/i })).toHaveAttribute("href", documentationUrl)
  })

  it("is a native button that opens with Enter", () => {
    renderPill()
    expect(pill().tagName).toBe("BUTTON")

    pill().focus()
    fireEvent.keyDown(pill(), { key: "Enter" })
    fireEvent.keyUp(pill(), { key: "Enter" })
    expect(screen.getByText("storage.url")).toBeInTheDocument()
  })

  it("closes on Escape", () => {
    renderPill()
    fireEvent.click(pill())
    expect(screen.getByText("storage.url")).toBeInTheDocument()

    fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" })
    expect(screen.queryByText("storage.url")).not.toBeInTheDocument()
  })
})
