import { TransactionMessage } from "./TransactionMessage.ts"

export interface TransactionResponse extends TransactionMessage {
  statusCode: number
}
