import { Page } from "Components/Page"
import { Tab } from "mkui/Components/Tabs"

import { SystemDependenciesTabPanel } from "./SystemDependenciesTabPanel.tsx"
import { SystemSettingsTabPanel } from "./SystemSettingsTabPanel.tsx"

const SystemPage = () => {
  return (
    <Page title="System" description="Informations about the running instance.">
      <Tab.Group>
        <Tab.List as="nav" aria-label="Tabs">
          <Tab>Settings</Tab>
          <Tab>Dependencies</Tab>
        </Tab.List>
        <Tab.Panels>
          <SystemSettingsTabPanel />
          <SystemDependenciesTabPanel />
        </Tab.Panels>
      </Tab.Group>
    </Page>
  )
}

export default SystemPage
