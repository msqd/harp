const DOCUMENTATION_BASE_URL = "https://docs.harp-proxy.net/en"
const DOCUMENTATION_CAMPAIGN = "utm_source=dashboard&utm_medium=help"

/**
 * Build the user documentation url for a given running version.
 *
 * Documentation is published per major.minor, so `0.10.0a2` and `0.10.3` both read `0.10`. Anything we cannot read a
 * version out of (development builds, an unreachable system api) falls back to the latest published documentation,
 * which is always a better answer than a dead link.
 */
export function getDocumentationUrl(version?: string): string {
  const parsed = version?.match(/^(\d+)\.(\d+)/)
  const target = parsed ? `${parsed[1]}.${parsed[2]}` : "latest"
  return `${DOCUMENTATION_BASE_URL}/${target}/user/?${DOCUMENTATION_CAMPAIGN}`
}
