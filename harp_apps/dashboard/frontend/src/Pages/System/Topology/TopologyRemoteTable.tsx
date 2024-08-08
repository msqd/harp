import { InboxIcon } from "@heroicons/react/24/outline"

import { Pane } from "ui/Components/Pane"

import StatusDropDown from "./StatusDropdown.tsx"

export default function TopologyRemoteTable({
  endpoint,
  remoteEndpoints,
  current_pool,
}: {
  endpoint: string
  remoteEndpoints: Settings.Proxy.RemoteEndpoint[]
  current_pool: string[]
}) {
  return (
    <Pane className="flex flex-col divide-y divide-gray-200">
      {remoteEndpoints.map((remoteEndpoint, j) => (
        <div key={j} className="flex items-center">
          <span className="inline-flex items-center gap-x-1 px-2 py-0.5 text-sm font-medium text-gray-800">
            {current_pool.includes(remoteEndpoint.url) ? (
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
            <a href={remoteEndpoint.url} className="hover:underline" target="_blank">
              {remoteEndpoint.url}
            </a>
          </span>
          <StatusDropDown endpoint={endpoint} remoteEndpoint={remoteEndpoint} />
          {remoteEndpoint.failure_reasons ? (
            <code className="inline-flex font-mono text-xs">{remoteEndpoint.failure_reasons.join(",")}</code>
          ) : null}
          {(remoteEndpoint.pools || ["default"]).map((pool, k) => (
            <span className="inline-flex items-center gap-x-1 rounded-full px-2 py-0.5 text-xs font-medium text-gray-500 ring-1 ring-inset ring-gray-200 mx-1">
              <InboxIcon key={k} className="size-3" /> {pool}
            </span>
          ))}
        </div>
      ))}
    </Pane>
  )
}
