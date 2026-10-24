import { ReactNode } from "react"

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

const Bar = ({ children }: { children: ReactNode }) => (
  <div className="flex h-14 items-center justify-end bg-primary-900 px-6">{children}</div>
)

/** Development-only settings are in use: the warning sign sits in the header. */
export const Default = () => (
  <Bar>
    <DevelopmentOnlyWarning settings={settings} />
  </Bar>
)

/** No development-only setting: nothing is rendered. */
export const NoSettings = () => (
  <Bar>
    <DevelopmentOnlyWarning settings={[]} />
  </Bar>
)
