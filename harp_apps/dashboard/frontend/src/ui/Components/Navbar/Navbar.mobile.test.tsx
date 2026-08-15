import { fireEvent, render, screen, within } from "@testing-library/react"
import { AriaAttributes, ReactNode } from "react"
import { To } from "react-router-dom"
import { describe, expect, it } from "vitest"

import { Navbar } from "./Navbar"

const items = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system" },
]

/**
 * Stands in for the router link the dashboard injects: an anchor with a real `href`, so the rendered markup carries
 * the `link` role a keyboard or screen reader user needs. Keeps this component's tests free of a router dependency.
 */
const Link = ({
  to,
  children,
  className,
  ...rest
}: {
  to: To
  children?: ReactNode
  className?: string
  "aria-current"?: AriaAttributes["aria-current"]
}) => (
  <a href={String(to)} className={className} {...rest}>
    {children}
  </a>
)

const menuButton = () => screen.getByRole("button", { name: "Open main menu" })

/**
 * The desktop links sit in the document at every viewport and are merely hidden by a css breakpoint, so counting
 * links proves nothing about what a phone can reach. These tests drive the menu button, which below the `sm`
 * breakpoint is the only way in.
 */
const openMenu = () => {
  const button = menuButton()
  fireEvent.click(button)
  const id = button.getAttribute("aria-controls")
  expect(id, "the menu button should point at the panel it opens").toBeTruthy()
  const panel = document.getElementById(id!)
  expect(panel).toBeInTheDocument()
  return panel!
}

describe("Navbar mobile menu", () => {
  it("keeps the menu closed until the menu button is pressed", () => {
    render(<Navbar Link={Link} items={items} />)

    expect(menuButton()).toHaveAttribute("aria-expanded", "false")
  })

  it("reveals every navigation item when the menu button is pressed", () => {
    render(<Navbar Link={Link} items={items} />)

    const panel = openMenu()

    for (const item of items) {
      expect(within(panel).getByRole("link", { name: item.label })).toHaveAttribute("href", item.to)
    }
  })

  it("marks the button as expanded once the menu is open", () => {
    render(<Navbar Link={Link} items={items} />)

    openMenu()

    expect(menuButton()).toHaveAttribute("aria-expanded", "true")
  })

  it("closes again when the button is pressed a second time", () => {
    render(<Navbar Link={Link} items={items} />)

    const panel = openMenu()
    fireEvent.click(menuButton())

    expect(menuButton()).toHaveAttribute("aria-expanded", "false")
    expect(panel).not.toBeInTheDocument()
  })

  it("closes the menu once a destination is chosen, so it stops covering the page", () => {
    render(<Navbar Link={Link} items={items} />)

    const panel = openMenu()
    fireEvent.click(within(panel).getByRole("link", { name: "System" }))

    expect(menuButton()).toHaveAttribute("aria-expanded", "false")
  })

  it("keeps secondary content reachable from the menu", () => {
    render(<Navbar Link={Link} items={items} rightChildren={<span>signed in as alice</span>} />)

    const panel = openMenu()

    expect(panel).toHaveTextContent("signed in as alice")
  })

  it("announces the current item rather than signalling it by colour alone", () => {
    render(<Navbar Link={Link} items={items} currentPath="/transactions" />)

    const panel = openMenu()

    expect(within(panel).getByRole("link", { name: "Transactions" })).toHaveAttribute("aria-current", "page")
    expect(within(panel).getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current")
  })
})
