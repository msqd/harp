import { render, screen } from "@testing-library/react"
import { ReactElement } from "react"
import { ResponsiveContainer } from "recharts"
import { expect, describe, vi, it } from "vitest"

import { TransactionsChart } from "./TransactionsChart"

interface ModuleWithResponsiveContainer {
  ResponsiveContainer: typeof ResponsiveContainer
}

vi.mock("recharts", async (OriginalModule) => {
  const mod = await OriginalModule<ModuleWithResponsiveContainer>()
  return {
    ...mod,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <mod.ResponsiveContainer width={800} height={800}>
        {children}
      </mod.ResponsiveContainer>
    ),
  }
})

describe("TransactionsChart", () => {
  it("renders without crashing", () => {
    type DataType = { datetime: string; count: number; errors: number }

    const data: DataType[] = [
      { datetime: "2022-01-01T00:00:00", count: 10, errors: 1 },
      { datetime: "2022-01-01T01:00:00", count: 20, errors: 2 },
    ]

    render(<TransactionsChart data={data} timeRange="1h" />)

    // Check that the component renders the correct data
    expect(screen.getByText("transactions")).toBeInTheDocument()
  })
})
