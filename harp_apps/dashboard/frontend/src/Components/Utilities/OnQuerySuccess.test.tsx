import { act, screen, waitFor } from "@testing-library/react"
import { ErrorBoundary } from "react-error-boundary"
import { useQuery } from "react-query"
import { describe, expect, it } from "vitest"

import { Error as ErrorScreen } from "Components/Page/Page.tsx"
import { renderWithClient } from "tests/utils.tsx"

import { OnQuerySuccess } from "./OnQuerySuccess.tsx"

function setup(fetcher: () => Promise<string>) {
  let refetch: () => Promise<unknown> = async () => undefined

  function Probe() {
    const query = useQuery("probe", fetcher)
    refetch = query.refetch
    return <OnQuerySuccess query={query}>{(q) => <div>data: {q.data}</div>}</OnQuerySuccess>
  }

  renderWithClient(
    <ErrorBoundary FallbackComponent={ErrorScreen}>
      <Probe />
    </ErrorBoundary>,
  )

  return { refetch: () => act(async () => void (await refetch())) }
}

describe("OnQuerySuccess", () => {
  it("keeps the data on screen with a notice when a refetch fails", async () => {
    let failing = false
    const { refetch } = setup(async () => {
      if (failing) throw new Error("backend down")
      return "fresh"
    })
    await screen.findByText("data: fresh")

    failing = true
    await refetch()

    expect(screen.getByText("data: fresh")).toBeTruthy()
    expect(screen.getByRole("status").textContent).toMatch(/could not be refreshed/i)
    expect(screen.queryByText(/Woopsie/)).toBeNull()
  })

  it("drops the notice by itself once the backend is back", async () => {
    let failing = false
    let value = "first"
    const { refetch } = setup(async () => {
      if (failing) throw new Error("backend down")
      return value
    })
    await screen.findByText("data: first")
    failing = true
    await refetch()
    await screen.findByRole("status")

    failing = false
    value = "second"
    await refetch()

    await waitFor(() => expect(screen.getByText("data: second")).toBeTruthy())
    expect(screen.queryByRole("status")).toBeNull()
  })

  it("shows the error screen when there is no data at all", async () => {
    setup(async () => {
      throw new Error("backend down")
    })

    expect(await screen.findByText(/Woopsie/)).toBeTruthy()
  })
})
