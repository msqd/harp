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

/** The header as the Layout builds it: the pill at the right end of the bar below `md`, right of the user from `md` up. */
const Header = ({ list }: { list: typeof settings }) => (
  <Navbar
    items={items}
    currentPath="/"
    leftChildren={<div className="text-white">HARP</div>}
    compactChildren={<DevelopmentOnlyWarning settings={list} documentationUrl={documentationUrl} />}
    rightChildren={
      <div className="flex items-center gap-3">
        <div className="text-right text-sm text-white">
          anonymous
          <br />
          <span className="text-xs">Help v.test version</span>
        </div>
        <DevelopmentOnlyWarning settings={list} documentationUrl={documentationUrl} className="hidden md:block" />
      </div>
    }
  />
)

/** Development-only settings are in use: an icon and the count sit in the header, right of the user. */
export const Default = () => <Header list={settings} />

/** Opened: each setting, what to use instead, and the documentation. */
export const Opened = () => <Header list={settings} />
Opened.meta = { openWith: "development-only settings" }

/** No development-only setting: nothing is rendered. */
export const NoSettings = () => <Header list={[]} />

/** Phone portrait, opened: the pill sits at the right end of the bar and the popover spans the screen. */
export const Phone = () => <Header list={settings} />
Phone.meta = { viewport: { width: 390, height: 844 }, openWith: "development-only settings" }

/** Small device in landscape: the hamburger layout, so the pill never pushes the navigation. */
export const Landscape = () => <Header list={settings} />
Landscape.meta = { viewport: { width: 667, height: 375 } }

/** Small device in landscape, opened: the popover scrolls rather than leave the screen. */
export const LandscapeOpened = () => <Header list={settings} />
LandscapeOpened.meta = { viewport: { width: 740, height: 360 }, openWith: "development-only settings" }
