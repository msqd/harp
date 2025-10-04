import { render, RenderResult } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "react-query"
import React from "react"

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

interface RenderWithClientResult extends Omit<RenderResult, "rerender"> {
  rerender: (rerenderUi: React.ReactNode) => void
}

export function renderWithClient(ui: React.ReactElement): RenderWithClientResult {
  const testQueryClient = createTestQueryClient()
  const { rerender, ...result } = render(<QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>)
  return {
    ...result,
    rerender: (rerenderUi: React.ReactNode) =>
      rerender(<QueryClientProvider client={testQueryClient}>{rerenderUi}</QueryClientProvider>),
  }
}

export function createWrapper() {
  const testQueryClient = createTestQueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={testQueryClient}>{children}</QueryClientProvider>
  )
}
