import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemSettingsQuery } from "Domain/System"
import { Pane } from "ui/Components/Pane"
import { Tab } from "ui/Components/Tabs"
import { H2 } from "ui/Components/Typography"

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
          // const endpoints = [{ name: "tejshshshshshshshsst", port: 1234, url: "test" }]
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
