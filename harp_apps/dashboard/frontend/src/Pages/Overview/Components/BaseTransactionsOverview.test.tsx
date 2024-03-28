import { render } from "@testing-library/react"
import { expect, it } from "vitest"

import { BaseTransactionsOverview, TransactionOverviewChartProps } from "./BaseTransactionsOverview"

it("renders without crashing", () => {
  const data: TransactionOverviewChartProps["data"] = {
    meanDuration: 2000,
    errors: { count: 2, rate: 0.05 },
    transactions: [],
    timeRange: "month",
    count: 100,
  }

  const { container } = render(<BaseTransactionsOverview data={data} title="Test Title" className="test-class" />)
  expect(container).toMatchSnapshot()
})
