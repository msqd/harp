import { Message, Transaction } from "Models/Transaction"

export const getResponseFromTransactionMessages = (transaction: Transaction) => {
  return transaction.messages?.find((message: Message) => message.kind === "response")
}
