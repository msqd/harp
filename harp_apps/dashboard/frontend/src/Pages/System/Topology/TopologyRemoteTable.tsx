import { InboxIcon } from "@heroicons/react/24/outline"

import { Pane } from "ui/Components/Pane"

import RemoteEndpointStatusDropDown from "./RemoteEndpointStatusDropDown.tsx"

export default function TopologyRemoteTable({
  endpointName,
  remote,
}: {
  endpointName: string
  remote?: Apps.Proxy.Remote
}) {
  if (!remote) {
    return <Pane className="flex flex-col divide-y divide-gray-200">no remote</Pane>
  }

  return (
    <Pane className="flex flex-col divide-y divide-gray-200">
      {remote.endpoints.map((remoteEndpoint, j) => (
        <div key={j} className="flex items-center">
          <span className="inline-flex items-center gap-x-1 px-2 py-0.5 text-sm font-medium text-gray-800">
            {remote.current_pool.includes(remoteEndpoint.settings.url) ? (
              <span title="Remote endpoint is active">
                <svg viewBox="0 0 6 6" aria-hidden="true" className="h-1.5 w-1.5 fill-blue-500">
                  <circle r={3} cx={3} cy={3} />
                </svg>
              </span>
            ) : (
              <span title="Remote endpoint is inactive">
                <svg viewBox="0 0 6 6" aria-hidden="true" className="h-1.5 w-1.5 fill-stone-300">
                  <circle r={3} cx={3} cy={3} />
                </svg>
              </span>
            )}
            <a href={remoteEndpoint.settings.url} className="hover:underline" target="_blank">
              {remoteEndpoint.settings.url}
            </a>
          </span>
          <RemoteEndpointStatusDropDown endpointName={endpointName} remoteEndpoint={remoteEndpoint} />
          {remoteEndpoint.failure_reasons ? (
            <code className="inline-flex font-mono text-xs">{remoteEndpoint.failure_reasons.join(",")}</code>
          ) : null}
          {(remoteEndpoint.settings.pools || ["default"]).map((pool, k) => (
            <span className="inline-flex items-center gap-x-1 rounded-full px-2 py-0.5 text-xs font-medium text-gray-500 ring-1 ring-inset ring-gray-200 mx-1">
              <InboxIcon key={k} className="size-3" /> {pool}
            </span>
          ))}
        </div>
      ))}
    </Pane>
  )
}
