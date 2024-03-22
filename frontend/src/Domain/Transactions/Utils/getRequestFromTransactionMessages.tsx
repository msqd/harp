import { Message, Transaction } from "Models/Transaction"

export const getRequestFromTransactionMessages: (transaction: Transaction) => {
  request?: Message
  endpoint?: string
} = (transaction) => {
  return {
    request: transaction.messages?.find((message: Message) => message.kind === "request") ?? undefined,
    endpoint: transaction.endpoint ?? undefined,
  }
}
