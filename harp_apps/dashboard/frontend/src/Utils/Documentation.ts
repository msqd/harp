const DOCUMENTATION_BASE_URL = "https://docs.harp-proxy.net/en"
const DOCUMENTATION_CAMPAIGN = "utm_source=dashboard&utm_medium=help"

/**
 * Build the user documentation url for a given running version.
 *
 * Documentation is published per major.minor, but only a final release `X.Y.Z` is guaranteed to have its `X.Y`
 * documentation line. Everything else (pre-releases, `.devN`, `git describe` strings, unknown or unreachable version)
 * opens the latest published documentation, which is always a better answer than a dead link.
 */
export function getDocumentationUrl(version?: string): string {
  const parsed = version?.match(/^(\d+)\.(\d+)\.\d+$/)
  const target = parsed ? `${parsed[1]}.${parsed[2]}` : "latest"
  return `${DOCUMENTATION_BASE_URL}/${target}/user/?${DOCUMENTATION_CAMPAIGN}`
}
