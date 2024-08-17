import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react"
import { ChevronDownIcon } from "@heroicons/react/20/solid"
import tw, { styled } from "twin.macro"

import { useSystemProxyMutation } from "Domain/System/useSystemProxyQuery.ts"

const StyledButtonMenuItem = styled.button`
  ${tw`block w-full px-2 py-1 text-left text-gray-700 data-[focus]:bg-gray-100 data-[focus]:text-gray-900`}
`
function getHumanStatus(status: number) {
  if (status > 0) {
    return "up"
  }
  if (status < 0) {
    return "down"
  }
  return "checking"
}

export default function RemoteEndpointStatusDropDown({
  endpointName,
  remoteEndpoint,
}: {
  endpointName: string
  remoteEndpoint: Apps.Proxy.RemoteEndpoint
}) {
  const mutation = useSystemProxyMutation()
  const status = remoteEndpoint.status ?? 0
  const humanStatus = getHumanStatus(status)

  return (
    <Menu as="div" className="relative text-left">
      <div className="flex">
        <MenuButton className="inline-flex w-full justify-center rounded bg-white px-2 py-0.5 text-xs text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 capitalize items-center gap-x-1 mx-1">
          {humanStatus == "up" && (
            <span title="Remote endpoint is up and running">
              <svg viewBox="0 0 6 6" aria-hidden="true" className="h-1.5 w-1.5 fill-green-500">
                <circle r={3} cx={3} cy={3} />
              </svg>
            </span>
          )}
          {humanStatus == "checking" && (
            <span title="Remote endpoint is half-open, will recheck the remote status conservatively.">
              <svg viewBox="0 0 6 6" aria-hidden="true" className="h-1.5 w-1.5 fill-yellow-500">
                <circle r={3} cx={3} cy={3} />
              </svg>
            </span>
          )}
          {humanStatus == "down" && (
            <span title="Remote endpoint is down, will not be used for routing.">
              <svg viewBox="0 0 6 6" aria-hidden="true" className="h-1.5 w-1.5 fill-red-500">
                <circle r={3} cx={3} cy={3} />
              </svg>
            </span>
          )}
          <span>{humanStatus}</span>
          <ChevronDownIcon aria-hidden="true" className="-mx-1 size-4 text-gray-400" />
        </MenuButton>
      </div>

      <MenuItems
        transition
        className="absolute text-xs left-0 z-10 mt-1 w-32 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 transition focus:outline-none data-[closed]:scale-95 data-[closed]:transform data-[closed]:opacity-0 data-[enter]:duration-100 data-[leave]:duration-75 data-[enter]:ease-out data-[leave]:ease-in"
      >
        <div className="py-1">
          {["up", "checking", "down"].map((status) =>
            humanStatus != status ? (
              <MenuItem key={status}>
                <StyledButtonMenuItem
                  type="button"
                  onClick={() =>
                    mutation.mutate({ endpoint: endpointName, url: remoteEndpoint.settings.url, action: status })
                  }
                >
                  Set {status}
                </StyledButtonMenuItem>
              </MenuItem>
            ) : null,
          )}
        </div>
      </MenuItems>
    </Menu>
  )
}
