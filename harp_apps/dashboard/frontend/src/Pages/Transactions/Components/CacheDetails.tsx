import { ReactNode } from "react"

const OUTCOME_HINTS: Record<string, string> = {
  hit: "Served from the cache, fresh.",
  stale: "Served from the cache as it was, though no longer fresh.",
  revalidated: "The origin confirmed the stored response (304), which was served.",
  miss: "Fetched from the origin.",
  uncacheable: "Fetched from the origin and not kept: the cache was not allowed to store it.",
}

/**
 * Compact duration: 90 -> "1m 30s", 3600 -> "1h", 0 -> "0s".
 */
function compactDuration(seconds: number): string {
  const parts: string[] = []
  for (const [unit, size] of [
    ["d", 86400],
    ["h", 3600],
    ["m", 60],
  ] as const) {
    if (seconds >= size) {
      parts.push(`${Math.floor(seconds / size)}${unit}`)
      seconds %= size
    }
  }
  if (seconds || !parts.length) parts.push(`${seconds}s`)
  return parts.join(" ")
}

function Row({
  label,
  title,
  children,
  mono = false,
}: {
  label: string
  title?: string
  children: ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex gap-x-2">
      <dt className="w-32 shrink-0 text-gray-500">{label}</dt>
      <dd
        aria-label={`Cache ${label.toLowerCase()}`}
        title={title}
        className={mono ? "font-mono break-all" : undefined}
      >
        {children}
      </dd>
    </div>
  )
}

/**
 * What the cache did for a transaction: the outcome, how old and how fresh the response was, and which entry served
 * it (cache key, variant, and the invalidation number the response is valid as of). Nothing if the cache did not see
 * the transaction.
 */
export function CacheDetails({ extras }: { extras?: { [k: string]: unknown } }) {
  const outcome = extras?.cache_outcome as string | undefined
  if (!outcome) return null
  const { cache_age: age, cache_ttl: ttl, cache_key: key, cache_variant: variant, cache_seq: seq } = extras ?? {}

  return (
    <dl className="text-xs space-y-1">
      <Row label="Outcome" title={OUTCOME_HINTS[outcome]}>
        {outcome}
      </Row>
      {typeof age === "number" ? <Row label="Age">{compactDuration(age)}</Row> : null}
      {typeof ttl === "number" ? <Row label="Freshness left">{compactDuration(ttl)}</Row> : null}
      {key ? (
        <Row label="Key" mono>
          {String(key)}
        </Row>
      ) : null}
      {variant ? (
        <Row label="Variant" mono>
          {String(variant)}
        </Row>
      ) : null}
      {typeof seq === "number" ? (
        <Row label="Invalidation number" title="The invalidation number the response is valid as of.">
          {seq}
        </Row>
      ) : null}
    </dl>
  )
}
