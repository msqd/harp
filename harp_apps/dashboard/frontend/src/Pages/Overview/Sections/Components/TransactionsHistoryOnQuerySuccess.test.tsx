import { render } from "@testing-library/react"
import { expect, it } from "vitest"

import {
  TransactionsHistoryOnQuerySuccess,
  TransactionsHistoryOnQuerySuccessProps,
} from "./TransactionsHistoryOnQuerySuccess.tsx"

it("renders without crashing", () => {
  const data: TransactionsHistoryOnQuerySuccessProps["data"] = {
    meanDuration: 2000,
    meanApdex: 85,
    errors: { count: 2, rate: 0.05 },
    transactions: [],
    timeRange: "month",
    count: 100,
  }

  const { container } = render(
    <TransactionsHistoryOnQuerySuccess data={data} title="Test Title" className="test-class" />,
  )
  expect(container).toMatchSnapshot()
})
