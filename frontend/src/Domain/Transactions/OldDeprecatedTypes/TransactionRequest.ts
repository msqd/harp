import { TransactionMessage } from "./TransactionMessage.ts"

export interface TransactionRequest extends TransactionMessage {
  method: string
  url: string
}
