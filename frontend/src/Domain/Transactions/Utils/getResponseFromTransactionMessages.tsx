import { Message, Transaction } from "Models/Transaction"

export const getResponseFromTransactionMessages = (transaction: Transaction) => {
  return {
    response: transaction.messages?.find((message: Message) => message.kind === "response"),
    error: transaction.messages?.find((message: Message) => message.kind === "error"),
  }
}
