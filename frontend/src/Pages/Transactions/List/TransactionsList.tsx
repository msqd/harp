import { TransactionDataTable } from "./TransactionDataTable.tsx"
import { Transaction } from "Models/Transaction"

interface TransactionsListProps {
  transactions: Transaction[]
}

export function TransactionsList({ transactions }: TransactionsListProps) {
  return (
    <>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-base font-semibold leading-6 text-gray-900">Transactions</h1>
          <p className="mt-2 text-sm text-gray-700">List of HTTP transactions</p>
        </div>
      </div>
      <div className="mt-8 flow-root">
        <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <TransactionDataTable transactions={transactions} />
          </div>
        </div>
      </div>
    </>
  )
}
