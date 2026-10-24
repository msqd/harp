import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "react-query"
import { createMemoryRouter, RouteObject, RouterProvider } from "react-router"
import { afterEach, expect, it, vi } from "vitest"

import { routes } from "./routes"

function renderAt(path: string, testRoutes: RouteObject[] = routes) {
  const router = createMemoryRouter(testRoutes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.restoreAllMocks())

it("renders an unknown URL inside the layout, with a link back to the overview", async () => {
  renderAt("/nope/at/all")

  expect(await screen.findByText(/page does not exist/i)).toBeInTheDocument()
  expect(screen.getAllByRole("link", { name: "Transactions" }).length).toBeGreaterThan(0)
  expect(screen.getByRole("link", { name: /back to the overview/i })).toHaveAttribute("href", "/")
})

it("does not present a render error as a 404, and logs it", async () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})
  const Boom = () => {
    throw new Error("kaboom")
  }
  const [layoutRoute] = routes
  const [guard] = layoutRoute.children!
  const [, ...otherPages] = guard.children!
  const guardWithBoom = { ...guard, children: [{ path: "", Component: Boom }, ...otherPages] } as RouteObject
  renderAt("/", [{ ...layoutRoute, children: [guardWithBoom] } as RouteObject])

  expect(await screen.findByText("kaboom")).toBeInTheDocument()
  expect(screen.queryByText(/page does not exist/i)).toBeNull()
  expect(consoleError).toHaveBeenCalled()
})
