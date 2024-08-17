import { PuzzlePieceIcon } from "@heroicons/react/24/outline"

import { Pane } from "ui/Components/Pane"

import TopologyRemoteTable from "./TopologyRemoteTable.tsx"

export function TopologyTable({ endpoints }: { endpoints: Apps.Proxy.Endpoint[] }) {
  return (
    <>
      {endpoints.map((endpoint, i) => (
        <Pane className="flex items-start" key={i}>
          <span className="inline-flex items-center gap-x-1 px-2 py-0.5 text-sm font-medium text-gray-800">
            <PuzzlePieceIcon className="size-4" />
            {endpoint.settings.name} ({endpoint.settings.port})
          </span>
          <TopologyRemoteTable endpointName={endpoint.settings.name} remote={endpoint.remote} />
        </Pane>
      ))}
    </>
  )
}
