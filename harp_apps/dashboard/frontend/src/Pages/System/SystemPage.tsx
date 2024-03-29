import { Page, PageTitle } from "Components/Page"
import { Tab } from "ui/Components/Tabs"

import { SystemDependenciesTabPanel } from "./SystemDependenciesTabPanel.tsx"
import { SystemSettingsTabPanel } from "./SystemSettingsTabPanel.tsx"
import { SystemStorageTabPanel } from "./SystemStorageTabPanel.tsx"

export const SystemPage = () => {
  return (
    <Page title={<PageTitle title="System" description="Informations about the running instance." />}>
      <Tab.Group>
        <Tab.List as="nav" aria-label="Tabs">
          <Tab>Settings</Tab>
          <Tab>Storage</Tab>
          <Tab>Dependencies</Tab>
        </Tab.List>
        <Tab.Panels>
          <SystemSettingsTabPanel />
          <SystemStorageTabPanel />
          <SystemDependenciesTabPanel />
        </Tab.Panels>
      </Tab.Group>
    </Page>
  )
}
