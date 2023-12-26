import { CheckIcon } from "@heroicons/react/20/solid"
import { XMarkIcon } from "@heroicons/react/24/outline"

import { KeyValueSettings, Setting } from "Domain/System/useSystemSettingsQuery"

function NullValue() {
  return (
    <>
      <XMarkIcon className="w-3 inline mr-1" />
      null
    </>
  )
}

function TrueValue() {
  return (
    <>
      <CheckIcon className="w-3 inline mr-1" />
      true
    </>
  )
}

function FalseValue() {
  return (
    <>
      <XMarkIcon className="w-3 inline mr-1" />
      false
    </>
  )
}

function Value({ value }: { value: Setting }) {
  if (value === null) {
    return <NullValue />
  }

  if (typeof value === "string" || typeof value == "number") {
    return value
  }

  if (typeof value == "boolean") {
    return value ? <TrueValue /> : <FalseValue />
  }

  return <ProxySettingsTable settings={value} />
}

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
                <Value value={value} />
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
