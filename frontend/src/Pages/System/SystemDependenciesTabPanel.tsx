import { Tab } from "@headlessui/react"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemDependenciesQuery } from "Domain/System"

import { SettingsTable } from "./Components"

export function SystemDependenciesTabPanel() {
  const query = useSystemDependenciesQuery()
  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
              <SettingsTable settings={query.data} />
            </div>
          )
        }}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
