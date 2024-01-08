import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemSettingsQuery } from "Domain/System"
import { Tab } from "mkui/Components/Tabs"

import { Topology } from "./Components/Topology/Topology"

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
            <div className="grid grid-cols-2 gap-4">
              <Topology endpoints={endpoints} title="Topology" className="border" />
            </div>
          )
        }}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
