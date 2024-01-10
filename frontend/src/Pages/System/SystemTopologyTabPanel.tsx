import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"
import { Pane } from "mkui/Components/Pane"
import { Tab } from "mkui/Components/Tabs"
import { H2 } from "mkui/Components/Typography"

import { Topology } from "./Components/Topology"

export function SystemTopologyTabPanel() {
  const query = useSystemSettingsQuery()
  interface ProxyData {
    endpoints?: { name: string; port: number; url: string; description?: string }[]
  }

  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => {
          const proxyData = query.data.proxy as ProxyData
          const endpoints = proxyData.endpoints
          return (
            <Pane>
              <H2>Topology</H2>
              <Topology endpoints={endpoints} />
            </Pane>
          )
        }}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
