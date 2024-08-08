import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemProxyQuery } from "Domain/System"
import { Pane } from "ui/Components/Pane"
import { Tab } from "ui/Components/Tabs"
import { H2 } from "ui/Components/Typography"

import { TopologyTable } from "./Topology/TopologyTable.tsx"

export function SystemTopologyTabPanel() {
  const query = useSystemProxyQuery()

  return (
    <OnQuerySuccess query={query}>
      {(query) => {
        return (
          <Tab.Panel>
            <Pane>
              <H2>Topology</H2>
              <TopologyTable endpoints={query.data.endpoints} />
            </Pane>
          </Tab.Panel>
        )
      }}
    </OnQuerySuccess>
  )
}
