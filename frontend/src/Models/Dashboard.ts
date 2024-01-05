export interface DashboardTransactionsReport {
  dailyStats: Array<{ date: string; transactions: number; errors: number }>
}

export interface DahsboardData extends DashboardTransactionsReport {
  errors: {
    count: number
    rate: number
  }
  transactions: {
    count: number
    meanDuration: number
  }
}
