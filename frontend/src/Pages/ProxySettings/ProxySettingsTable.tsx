import { KeyValueSettings } from "Domain/ProxySettings/useProxySettingsQuery.ts"
import { CheckIcon } from "@heroicons/react/20/solid"
import { XMarkIcon } from "@heroicons/react/24/outline"

export const ProxySettingsTable = ({ settings }: { settings: KeyValueSettings }) => {
  return (
    <table className="min-w-fit divide-y divide-gray-300">
      <tbody className="divide-y divide-gray-200 bg-white">
        {Object.entries(settings).map(([key, value]) => {
          return (
            <tr key={key}>
              <td className="whitespace-nowrap py-2 px-4 text-sm font-medium text-gray-900 min-w-fit align-top">
                {key}
              </td>
              <td className="whitespace-nowrap text-sm text-gray-500">
                {typeof value === "string" ? (
                  value
                ) : typeof value == "boolean" ? (
                  value ? (
                    <>
                      <CheckIcon className="w-3 inline mr-1" />
                      true
                    </>
                  ) : (
                    <>
                      <XMarkIcon className="w-3 inline mr-1" />
                      false
                    </>
                  )
                ) : (
                  <ProxySettingsTable settings={value} />
                )}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
