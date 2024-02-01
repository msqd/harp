import * as Bokeh from "@bokeh/bokehjs/build/js/lib"
import { JsonItem } from "@bokeh/bokehjs/build/js/lib/embed"
import { useEffect } from "react"

import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemTopologyQuery } from "Domain/System"
import { Pane } from "mkui/Components/Pane"
import { Tab } from "mkui/Components/Tabs"
import { H2 } from "mkui/Components/Typography"

import "@bokeh/bokehjs/build/js/lib/models/main"

function Plot({ data }: { data: JsonItem }) {
  useEffect(() => {
    Bokeh.embed.embed_item(data, "testplot").catch((err) => {
      throw err
    })
  }, [])

  return <div id="testplot"></div>
}

export function SystemTopologyTabPanel() {
  const query = useSystemTopologyQuery()

  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <Pane>
              <H2>Topology</H2>
              <Plot data={query.data as JsonItem} />
            </Pane>
          )
        }}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
