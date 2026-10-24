import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react"
import { ExclamationTriangleIcon } from "@heroicons/react/20/solid"

export interface DevelopmentOnlySetting {
  /** The setting, as the operator writes it. */
  name: string
  /** What is wrong with it and what to use instead. */
  message: string
}

interface DevelopmentOnlyWarningProps {
  settings: DevelopmentOnlySetting[]
}

/**
 * Warning sign for the header: shown only when the instance runs with settings that are fine on a laptop and unsafe in
 * production. Clicking it lists each setting and what to use instead.
 */
function DevelopmentOnlyWarning({ settings }: DevelopmentOnlyWarningProps) {
  if (settings.length === 0) {
    return null
  }
  return (
    <Popover className="relative">
      <PopoverButton
        title="Development-only settings in use"
        className="mr-4 rounded p-1 text-yellow-300 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
      >
        <span className="sr-only">Development-only settings in use</span>
        <ExclamationTriangleIcon className="h-6 w-6" aria-hidden="true" />
      </PopoverButton>
      <PopoverPanel className="absolute right-0 z-50 mt-2 w-96 max-w-[90vw] rounded bg-white p-3 text-left text-sm text-gray-900 shadow-lg ring-1 ring-black/10">
        <p className="mb-2 font-medium">Development-only settings in use</p>
        <ul className="space-y-2">
          {settings.map((setting) => (
            <li key={setting.name}>
              <code className="font-mono font-medium">{setting.name}</code>
              <p className="text-gray-700">{setting.message}</p>
            </li>
          ))}
        </ul>
      </PopoverPanel>
    </Popover>
  )
}

export { DevelopmentOnlyWarning }
