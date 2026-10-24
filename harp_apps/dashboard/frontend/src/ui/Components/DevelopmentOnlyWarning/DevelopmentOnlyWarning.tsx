import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react"
import { BeakerIcon } from "@heroicons/react/20/solid"

import { classNames } from "../../Utilities"

export interface DevelopmentOnlySetting {
  /** The setting, as the operator writes it. */
  name: string
  /** What is wrong with it and what to use instead. */
  message: string
}

interface DevelopmentOnlyWarningProps {
  settings: DevelopmentOnlySetting[]
  /** Where "going to production" is documented. */
  documentationUrl: string
  className?: string
}

const TITLE = "Development-only settings in use"

/**
 * Pill for the header: shown only when the instance runs with settings that are fine on a laptop and unsafe in
 * production. The label stays short ("Dev 3") so it fits a phone in landscape; the popover carries the full text, each
 * setting, what to use instead, and the documentation.
 */
function DevelopmentOnlyWarning({ settings, documentationUrl, className }: DevelopmentOnlyWarningProps) {
  if (settings.length === 0) {
    return null
  }
  return (
    <Popover className={classNames("relative", className)}>
      <PopoverButton
        aria-label={`${TITLE}: ${settings.length}`}
        className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-amber-100 px-2.5 py-1 sm:gap-0.5 sm:px-1 md:gap-1 md:px-2.5 text-xs font-semibold text-amber-950 ring-1 ring-amber-300 hover:bg-amber-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
      >
        <BeakerIcon className="h-4 w-4" aria-hidden="true" />
        {/* Between `sm` and `md` the header is full: only the icon and the count stay. */}
        <span aria-hidden="true" className="sm:hidden md:inline">
          Dev
        </span>
        <span
          aria-hidden="true"
          className="rounded-full bg-amber-950 px-1.5 text-[10px] leading-4 text-amber-100 sm:px-1 md:px-1.5"
        >
          {settings.length}
        </span>
      </PopoverButton>
      <PopoverPanel className="fixed inset-x-4 top-14 z-50 max-h-[calc(100vh-4.5rem)] overflow-y-auto rounded-lg bg-white p-4 text-left text-sm text-gray-900 shadow-lg ring-1 ring-black/10 sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-96">
        <p className="mb-1 font-semibold">{TITLE}</p>
        <p className="mb-3 text-gray-600">Fine on a laptop, not for production. What to change:</p>
        <ul className="divide-y divide-amber-200">
          {settings.map((setting) => (
            <li key={setting.name} className="py-2 first:pt-0 last:pb-0">
              <code className="rounded bg-amber-100 px-1 font-mono font-medium text-amber-950">{setting.name}</code>
              <p className="mt-1 text-gray-800">{setting.message}</p>
            </li>
          ))}
        </ul>
        <a
          className="mt-3 inline-block font-medium text-primary-800 underline"
          href={documentationUrl}
          target="_blank"
          rel="noreferrer"
        >
          Going to production (documentation)
        </a>
      </PopoverPanel>
    </Popover>
  )
}

export { DevelopmentOnlyWarning }
