export interface OverviewTransactionsReport {
  transactions: Array<{ datetime: string; count: number; errors: number }>
}

export interface OverviewData extends OverviewTransactionsReport {
  errors: {
    count: number
    rate: number
  }
  count: number
  meanDuration: number
  meanTpdex: number
  timeRange: string
}
