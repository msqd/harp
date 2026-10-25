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
