export interface OverviewTransactionsReport {
  dailyStats: Array<{ date: string; transactions: number; errors: number }>
}

export interface OverviewData extends OverviewTransactionsReport {
  errors: {
    count: number
    rate: number
  }
  transactions: {
    count: number
    meanDuration: number
  }
}
