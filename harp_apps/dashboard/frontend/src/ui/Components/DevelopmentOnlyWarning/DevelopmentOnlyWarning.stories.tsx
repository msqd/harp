import { Navbar } from "ui/Components/Navbar"

import { DevelopmentOnlyWarning } from "./DevelopmentOnlyWarning"

const settings = [
  { name: "storage.url", message: "SQLite storage is meant for development: use PostgreSQL in production." },
  {
    name: "dashboard.auth.type",
    message:
      "Dashboard authentication is disabled (dashboard.auth.type=none): the dashboard is unauthenticated and exposes proxied traffic to anyone who can reach its port. Use dashboard.auth.type=basic.",
  },
  {
    name: "HARP_DEBUG",
    message: "Debug mode is on and may leak tracebacks in error responses: unset HARP_DEBUG in production.",
  },
]

const items = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system" },
]

const documentationUrl = "https://docs.harp-project.net/en/latest/user/"

/** The header as the Layout builds it: the pill beside the logo below `sm`, beside the user from `sm` up. */
const Header = ({ list }: { list: typeof settings }) => (
  <Navbar
    items={items}
    currentPath="/"
    leftChildren={
      <div className="flex items-center text-white">
        HARP
        <DevelopmentOnlyWarning settings={list} documentationUrl={documentationUrl} className="ml-3 sm:hidden" />
      </div>
    }
    rightChildren={
      <div className="text-right text-sm text-white">
        <div className="flex items-center justify-end gap-2">
          <DevelopmentOnlyWarning settings={list} documentationUrl={documentationUrl} className="hidden sm:block" />
          <span>anonymous</span>
        </div>
        <span className="text-xs">Help v.test version</span>
      </div>
    }
  />
)

/** Development-only settings are in use: a short pill sits in the header. */
export const Default = () => <Header list={settings} />

/** Opened: each setting, what to use instead, and the documentation. */
export const Opened = () => <Header list={settings} />
Opened.meta = { openWith: "development-only settings" }

/** No development-only setting: nothing is rendered. */
export const NoSettings = () => <Header list={[]} />

/** Phone portrait, opened: the pill stays in the header bar and the popover spans the screen. */
export const Phone = () => <Header list={settings} />
Phone.meta = { viewport: { width: 390, height: 844 }, openWith: "development-only settings" }

/** Small device in landscape: the pill fits without wrapping or pushing the navigation. */
export const Landscape = () => <Header list={settings} />
Landscape.meta = { viewport: { width: 667, height: 375 } }

/** Small device in landscape, opened: the popover scrolls rather than leave the screen. */
export const LandscapeOpened = () => <Header list={settings} />
LandscapeOpened.meta = { viewport: { width: 740, height: 360 }, openWith: "development-only settings" }
