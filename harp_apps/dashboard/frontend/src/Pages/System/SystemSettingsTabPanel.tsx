import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"
import { Pane } from "ui/Components/Pane"
import { Tab } from "ui/Components/Tabs"

import { SettingsTable } from "./Components"

export function SystemSettingsTabPanel() {
  const query = useSystemSettingsQuery()

  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => (
          <Pane hasDefaultPadding={false}>
            <SettingsTable settings={query.data} />
          </Pane>
        )}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
