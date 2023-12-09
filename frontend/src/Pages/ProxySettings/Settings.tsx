import { useProxySettingsQuery } from "Domain/ProxySettings"
import { useEffect, useState } from "react"
import { KeyValueSettings } from "Domain/ProxySettings/useProxySettingsQuery.ts"
import { CheckIcon } from "@heroicons/react/20/solid"
import { XMarkIcon } from "@heroicons/react/24/outline"

const SettingsTable = ({ settings }: { settings: KeyValueSettings }) => {
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
                  <SettingsTable settings={value} />
                )}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

const Settings = () => {
  const query = useProxySettingsQuery()
  const [settings, setSettings] = useState<KeyValueSettings | null>(null)

  useEffect(() => {
    if (query.data) {
      setSettings(query.data)
    }
  }, [query.data])

  return (
    <>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-base font-semibold leading-6 text-gray-900">Settings</h1>
          <p className="mt-2 text-sm text-gray-700">Dump of actually applied configuration</p>
        </div>
      </div>
      <div className="mt-8 flow-root">
        <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
              {settings ? <SettingsTable settings={settings} /> : null}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default Settings
