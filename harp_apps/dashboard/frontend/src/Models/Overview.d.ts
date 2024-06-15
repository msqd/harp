export interface OverviewTransaction {
  datetime: string
  count: number
  errors: number
  cached: number
}
export interface OverviewTransactionsReport {
  transactions: Array<OverviewTransaction>
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
