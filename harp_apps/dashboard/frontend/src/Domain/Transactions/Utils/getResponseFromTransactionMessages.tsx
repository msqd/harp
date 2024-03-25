import { Message, Transaction } from "Models/Transaction"

export const getResponseFromTransactionMessages: (transation: Transaction) => {
  response?: Message
  error?: Message
  endpoint?: string
} = (transaction) => {
  return {
    response: transaction.messages?.find((message: Message) => message.kind === "response") ?? undefined,
    error: transaction.messages?.find((message: Message) => message.kind === "error") ?? undefined,
    endpoint: transaction.endpoint ?? undefined,
  }
}
