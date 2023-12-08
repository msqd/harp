export interface TransactionMessage {
  id: string
  headers?: Record<string, string>
  content?: string | null
}
