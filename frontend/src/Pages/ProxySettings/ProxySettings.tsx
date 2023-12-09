import { useProxySettingsQuery } from "Domain/ProxySettings"
import { KeyValueSettings } from "Domain/ProxySettings/useProxySettingsQuery.ts"
import { CheckIcon } from "@heroicons/react/20/solid"
import { XMarkIcon } from "@heroicons/react/24/outline"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { Page } from "Components/Page"

const ProxySettingsTable = ({ settings }: { settings: KeyValueSettings }) => {
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

const ProxySettings = () => {
  const query = useProxySettingsQuery()

  return (
    <Page title="Settings" description="Dump of actually applied configuration">
      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
              <ProxySettingsTable settings={query.data} />
            </div>
          )
        }}
      </OnQuerySuccess>
    </Page>
  )
}

export default ProxySettings
