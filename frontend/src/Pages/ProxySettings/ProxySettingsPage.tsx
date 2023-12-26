import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"

import { ProxySettingsTable } from "./ProxySettingsTable"

const ProxySettingsPage = () => {
  const query = useSystemSettingsQuery()

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

export default ProxySettingsPage
