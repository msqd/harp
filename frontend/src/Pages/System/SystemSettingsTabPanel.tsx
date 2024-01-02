import { Tab } from "@headlessui/react"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemSettingsQuery } from "Domain/System"

import { SettingsTable } from "./Components"

export function SystemSettingsTabPanel() {
  const query = useSystemSettingsQuery()

  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => (
          <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
            <SettingsTable settings={query.data} />
          </div>
        )}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
