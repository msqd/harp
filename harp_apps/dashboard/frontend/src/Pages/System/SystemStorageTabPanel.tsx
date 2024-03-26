import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemStorageQuery } from "Domain/System"
import { KeyValueSettings, Setting } from "Domain/System/useSystemSettingsQuery.ts"
import { Pane } from "ui/Components/Pane"
import { Tab } from "ui/Components/Tabs"

import { SettingsTable } from "./Components"

export function SystemStorageTabPanel() {
  const query = useSystemStorageQuery()

  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => (
          <Pane hasDefaultPadding={false}>
            <SettingsTable settings={query.data as KeyValueSettings | Array<Setting>} />
          </Pane>
        )}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
