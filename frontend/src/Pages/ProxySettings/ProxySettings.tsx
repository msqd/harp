import { useProxySettingsQuery } from "Domain/ProxySettings"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { Page } from "Components/Page"
import { ProxySettingsTable } from "./ProxySettingsTable"

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
