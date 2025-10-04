import { lazy } from "react"

// Export types for TypeScript declaration generation
export type { TransactionsChartProps } from "./TransactionsChart"

export const TransactionsChart = lazy(() => import("./TransactionsChart.tsx"))
export const SummaryPerformancesChart = lazy(() => import("./SummaryPerformancesChart.tsx"))
export const SummaryRateChart = lazy(() => import("./SummaryRateChart.tsx"))
