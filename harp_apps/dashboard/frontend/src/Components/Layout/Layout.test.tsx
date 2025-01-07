import { MemoryRouter } from "react-router-dom"
import { expect, it } from "vitest"

import { renderWithClient } from "tests/utils"

import { default as Layout } from "./Layout"

it("renders the title and data when the query is successful", async () => {
  const navigationItems = [
    { label: "Overview", to: "/", exact: true },
    { label: "Transactions", to: "/transactions" },
    { label: "System", to: "/system" },
  ]
  const result = renderWithClient(
    <MemoryRouter>
      <Layout title="Harp EA" navigationItems={navigationItems} />
    </MemoryRouter>,
  )

  await result.findByText("v.test version")
  expect(result.container).toMatchSnapshot()
})
