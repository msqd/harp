interface TransactionRequest {
  method: string;
  url: string;
  headers: any;
  body: any;
}

interface TransactionResponse {
  statusCode: number;
  headers: any;
  body: any;
}

export interface Transaction {
  id: string;
  request: TransactionRequest | null;
  response: TransactionResponse | null;
  createdAt: string;
}
