import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"
import { Pane } from "mkui/Components/Pane"
import { Tab } from "mkui/Components/Tabs"

import { SettingsTable } from "./Components"

export function SystemSettingsTabPanel() {
  const query = useSystemSettingsQuery()

  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => (
          <Pane usePadding={false} className="p-0">
            <SettingsTable settings={query.data} />
          </Pane>
        )}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
