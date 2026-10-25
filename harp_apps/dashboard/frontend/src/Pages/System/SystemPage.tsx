import { Helmet } from "react-helmet"

import { Page, PageTitle } from "Components/Page"
import { Role, roleIncludes, useRole } from "Domain/System"
import { Tab } from "ui/Components/Tabs"

import { SystemDependenciesTabPanel } from "./SystemDependenciesTabPanel.tsx"
import { SystemSettingsTabPanel } from "./SystemSettingsTabPanel.tsx"
import { SystemStorageTabPanel } from "./SystemStorageTabPanel.tsx"
import { SystemTopologyTabPanel } from "./SystemTopologyTabPanel.tsx"

/** The role each tab needs: the server refuses the others, so they are not offered. */
const TABS: { label: string; requires: Role; Panel: () => JSX.Element }[] = [
  { label: "Topology", requires: "editor", Panel: SystemTopologyTabPanel },
  { label: "Settings", requires: "admin", Panel: SystemSettingsTabPanel },
  { label: "Storage", requires: "editor", Panel: SystemStorageTabPanel },
  { label: "Dependencies", requires: "admin", Panel: SystemDependenciesTabPanel },
]

const SystemPage = () => {
  const role = useRole()
  const tabs = TABS.filter(({ requires }) => roleIncludes(role, requires))

  return (
    <Page title={<PageTitle title="System" description="Informations about the running instance." />}>
      <Helmet>
        <title>System | HARP</title>
        <meta name="description" content="System page" />
      </Helmet>
      {tabs.length === 0 ? (
        <p className="text-sm text-gray-700">The system pages need the Editor role.</p>
      ) : (
        <Tab.Group>
          <Tab.List as="nav" aria-label="Tabs">
            {tabs.map(({ label }) => (
              <Tab key={label}>{label}</Tab>
            ))}
          </Tab.List>
          <Tab.Panels>
            {tabs.map(({ label, Panel }) => (
              <Panel key={label} />
            ))}
          </Tab.Panels>
        </Tab.Group>
      )}
    </Page>
  )
}

export default SystemPage
