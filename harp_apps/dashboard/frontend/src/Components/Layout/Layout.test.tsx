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

// Keep these below the snapshot test: the ids in the snapshot count the components rendered before it.
const navigationItems = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system", requires: "editor" as const },
]

function renderAs(role: string, extra = {}) {
  server.use(
    http.get("/api/system", () =>
      HttpResponse.json({ version: "test version", revision: "r", user: "alice", role, ...extra }),
    ),
  )
  return renderWithClient(
    <MemoryRouter>
      <Layout navigationItems={navigationItems} />
    </MemoryRouter>,
  )
}

it("shows the account and its role in the header", async () => {
  const result = renderAs("editor", { displayName: "Alice A." })

  await result.findByText("Alice A.")
  expect(result.getByText("editor")).toBeTruthy()
})

it("falls back to the username when the account has no display name", async () => {
  const result = renderAs("viewer")

  expect(await result.findByText("alice")).toBeTruthy()
  expect(result.getByText("viewer")).toBeTruthy()
})

it("does not offer the system pages to a viewer", async () => {
  const result = renderAs("viewer")

  await result.findByText("viewer")
  expect(result.queryAllByText("System")).toEqual([])
  expect(result.queryAllByText("Transactions").length).toBeGreaterThan(0)
})

it("offers the system pages to an editor", async () => {
  const result = renderAs("editor")

  await result.findByText("editor")
  expect(result.queryAllByText("System").length).toBeGreaterThan(0)
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
