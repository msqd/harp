import { render, screen } from "@testing-library/react"
import { expect, it } from "vitest"

import { NotFound } from "./NotFound"

it("exposes the title as the page heading and renders the action", () => {
  render(
    <NotFound title="Gone" action={<a href="/">Home</a>}>
      Explanation
    </NotFound>,
  )
  expect(screen.getByRole("heading", { level: 1, name: "Gone" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument()
})

it("offers no action when none is given", () => {
  render(<NotFound title="Gone" />)
  expect(screen.queryByRole("link")).toBeNull()
})
