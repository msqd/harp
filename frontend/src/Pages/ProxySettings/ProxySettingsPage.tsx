import { Tab } from "@headlessui/react"
import { Fragment, ReactNode } from "react"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useSystemDependenciesQuery, useSystemSettingsQuery } from "Domain/System"
import { classNames } from "mkui/Utilities"

import { ProxySettingsTable } from "./ProxySettingsTable"

const StyledTab = ({ children }: { children: ReactNode }) => {
  return (
    <Tab as={Fragment}>
      {({ selected }) => (
        <a
          href="#"
          className={classNames(
            selected ? "bg-indigo-100 text-indigo-700" : "text-gray-500 hover:text-gray-700",
            "rounded-md px-3 py-2 text-sm font-medium",
          )}
          aria-current={selected ? "page" : undefined}
        >
          {children}
        </a>
      )}
    </Tab>
  )
}

const ProxySettingsPage = () => {
  const settingsQuery = useSystemSettingsQuery()
  const dependenciesQuery = useSystemDependenciesQuery()

  return (
    <Page title="Settings" description="Dump of actually applied configuration">
      <Tab.Group>
        <nav className="flex space-x-4 mb-4" aria-label="Tabs">
          <Tab.List>
            <StyledTab>Settings</StyledTab>
            <StyledTab>Dependencies</StyledTab>
          </Tab.List>
        </nav>
        <Tab.Panels>
          <Tab.Panel>
            <OnQuerySuccess query={settingsQuery}>
              {(query) => {
                return (
                  <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
                    <ProxySettingsTable settings={query.data} />
                  </div>
                )
              }}
            </OnQuerySuccess>
          </Tab.Panel>
          <Tab.Panel>
            <OnQuerySuccess query={dependenciesQuery}>
              {(query) => {
                return (
                  <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
                    <ProxySettingsTable settings={query.data} />
                  </div>
                )
              }}
            </OnQuerySuccess>
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </Page>
  )
}

export default ProxySettingsPage
