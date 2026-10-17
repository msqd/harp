import { act, renderHook } from "@testing-library/react"
import { ReactNode } from "react"
import { focusManager, onlineManager, QueryClient, QueryClientProvider } from "react-query"
import { afterEach, expect, it, vi } from "vitest"

import { useTransactionsListQuery } from "./useTransactionsListQuery"

const { fetch } = vi.hoisted(() => ({ fetch: vi.fn() }))
vi.mock("Domain/Api", () => ({ useApi: () => ({ fetch }) }))

afterEach(() => {
  focusManager.setFocused(undefined)
  onlineManager.setOnline(true)
  vi.useRealTimers()
})

it("pauses automatic updates while preserving cached data and manual refresh, then resumes", async () => {
  vi.useFakeTimers()
  focusManager.setFocused(true)
  const data = { items: [{ id: "ABCD1234" }], total: 1, pages: 1, perPage: 20 }
  fetch.mockResolvedValue({ json: async () => data })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  const result = renderHook(({ paused }) => useTransactionsListQuery({ paused }), {
    initialProps: { paused: true },
    wrapper,
  })
  await act(() => vi.advanceTimersByTimeAsync(1))
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(result.result.current.data).toEqual(data)

  await act(() => vi.advanceTimersByTimeAsync(30000))
  await act(async () => {
    focusManager.setFocused(false)
    focusManager.setFocused(true)
    await vi.advanceTimersByTimeAsync(1)
  })
  await act(async () => {
    onlineManager.setOnline(false)
    onlineManager.setOnline(true)
    await vi.advanceTimersByTimeAsync(1)
  })
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(result.result.current.data).toEqual(data)

  await act(async () => {
    await client.invalidateQueries(["transactions"])
    await vi.advanceTimersByTimeAsync(1)
  })
  expect(fetch).toHaveBeenCalledTimes(2)
  expect(result.result.current.data).toEqual(data)

  result.rerender({ paused: false })
  await act(() => vi.advanceTimersByTimeAsync(10000))
  expect(fetch).toHaveBeenCalledTimes(3)
  await act(async () => {
    focusManager.setFocused(false)
    focusManager.setFocused(true)
    await vi.advanceTimersByTimeAsync(1)
  })
  expect(fetch).toHaveBeenCalledTimes(4)
  result.unmount()
  client.clear()
})
