export function HeadersTable({ headers }: { headers: Record<string, string> }) {
  return (
    <table className="divide-y">
      <tbody className="divide-y divide-gray-200 bg-white">
        {Object.entries(headers).map(([k, v], index) => (
          <tr key={index}>
            <td className="whitespace-nowrap py-1 pl-4 pr-3 text-sm text-gray-500 sm:pl-0">{k}</td>
            <td className="whitespace-nowrap px-2 py-1 text-sm text-gray-900">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
