import { PuzzlePieceIcon } from "@heroicons/react/24/outline"

import { Pane } from "ui/Components/Pane"

import TopologyRemoteTable from "./TopologyRemoteTable.tsx"

export function TopologyTable({ endpoints }: { endpoints: Apps.Proxy.Endpoint[] }) {
  return (
    <>
      {endpoints.map((endpoint, i) => (
        <Pane className="flex items-start overflow-auto space-x-1" key={i}>
          <span className="flex gap-x-2 px-2 py-0.5 text-sm font-medium text-gray-800 items-center ">
            <PuzzlePieceIcon className="size-4" />
            <span className="flex flex-col text-center">
              {endpoint.settings.name}
              {endpoint.settings.port ? (
                <span className="inline-flex items-center gap-x-1 rounded-full px-2 py-0.5 text-xs font-medium text-gray-500 ring-1 ring-inset ring-gray-200 mx-1">
                  {endpoint.settings.port}
                </span>
              ) : (
                <p className="text-xs font-medium text-gray-400 mx-1">not exposed</p>
              )}
            </span>
          </span>
          <TopologyRemoteTable endpointName={endpoint.settings.name} remote={endpoint.remote} />
        </Pane>
      ))}
    </>
  )
}
