import { Message, Transaction } from "Models/Transaction"

export const getRequestFromTransactionMessages = (transaction: Transaction) => {
  return transaction.messages?.find((message: Message) => message.kind === "request")
}
