import { TransactionRequest } from "./TransactionRequest"
import { TransactionResponse } from "./TransactionResponse"

export interface Transaction {
  id: string
  endpoint: string | null
  request: TransactionRequest | null
  response: TransactionResponse | null
  createdAt: string
}
