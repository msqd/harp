import { http, HttpResponse } from "msw"
import { MemoryRouter } from "react-router"
import { expect, it } from "vitest"

import { server } from "tests/mocks/node"
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

const renderLayout = () =>
  renderWithClient(
    <MemoryRouter>
      <Layout navigationItems={[]} />
    </MemoryRouter>,
  )

it("warns about development-only settings in use", async () => {
  server.use(
    http.get("/api/system", () =>
      HttpResponse.json({
        version: "test version",
        revision: "test revision",
        development_only_settings: [{ name: "storage.url", message: "use PostgreSQL in production." }],
      }),
    ),
  )
  const result = renderLayout()

  await result.findByText("v.test version")
  // One pill at the right end of the bar below `md`, one right of the user block from `md` up; CSS shows one.
  const pills = result.getAllByRole("button", { name: /development-only settings in use: 1/i })
  expect(pills).toHaveLength(2)
  expect(pills.filter((pill) => pill.parentElement?.classList.contains("hidden"))).toHaveLength(1)
  expect(pills.some((pill) => pill.closest(".md\\:hidden"))).toBe(true)
})

it("shows no warning when no development-only setting is in use", async () => {
  server.use(
    http.get("/api/system", () =>
      HttpResponse.json({ version: "test version", revision: "test revision", development_only_settings: [] }),
    ),
  )
  const result = renderLayout()

  await result.findByText("v.test version")
  expect(result.queryByRole("button", { name: /development-only settings/i })).not.toBeInTheDocument()
})
