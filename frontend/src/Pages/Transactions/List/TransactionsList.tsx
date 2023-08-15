import { Transaction } from "Domain/Transactions.tsx";

/*


        <ul>
          {query.data.items.map((transaction, i) => (
            <li key={i}>
              {transaction.request ? (
                <>
                  <span>{transaction.request.method}</span>{" "}
                  <span>{transaction.request.url}</span>
                </>
              ) : (
                "-"
              )}{" "}
              →{" "}
              {transaction.response ? (
                <>{transaction.response.statusCode}</>
              ) : (
                "-"
              )}
            </li>
          ))}
        </ul>
 */

interface TransactionsListProps {
  transactions: Transaction[];
}

export function TransactionsList({ transactions }: TransactionsListProps) {
  return (
    <div className="py-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-base font-semibold leading-6 text-gray-900">
            Transactions
          </h1>
          <p className="mt-2 text-sm text-gray-700">
            List of HTTP transactions
          </p>
        </div>
      </div>
      <div className="mt-8 flow-root">
        <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <table className="min-w-full divide-y divide-gray-300 text-left">
              <thead>
                <tr>
                  <th
                    scope="col"
                    className="whitespace-nowrap py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-0 w-1"
                  >
                    ID
                  </th>
                  <th
                    scope="col"
                    className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1"
                  >
                    Method
                  </th>
                  <th
                    scope="col"
                    className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1"
                  >
                    URL
                  </th>
                  <th
                    scope="col"
                    className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1"
                  >
                    Status Code
                  </th>
                  <th
                    scope="col"
                    className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900"
                  >
                    Request
                  </th>
                  <th
                    scope="col"
                    className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900"
                  >
                    Response
                  </th>
                  <th
                    scope="col"
                    className="whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900 w-1"
                  >
                    Timestamp
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {transactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="whitespace-nowrap py-2 pl-4 pr-3 text-sm text-gray-500 sm:pl-0 font-mono">
                      {transaction.id}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-sm font-medium text-gray-900">
                      {transaction.request?.method || "-"}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-sm font-medium text-gray-900">
                      {transaction.request?.url || "-"}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-900">
                      {transaction.response?.statusCode ? (
                        <span className="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                          {/* vert bleu jaune ou rouge */}
                          {transaction.response.statusCode}
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-900">
                      -
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-900">
                      -
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-sm text-gray-900">
                      {transaction.createdAt}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
