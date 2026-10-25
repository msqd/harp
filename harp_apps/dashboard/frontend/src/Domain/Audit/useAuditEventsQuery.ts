import { useQuery } from "react-query"

import { useApi } from "Domain/Api"
import { ItemList } from "Domain/Api/Types"

export interface AuditEvent {
  id: number
  occurredAt: string
  action: string
  outcome: "succeeded" | "failed" | "denied"
  actor: { id: number | null; label: string | null; via: string; viaId: string | null; client: string | null }
  ip: string | null
  userAgent: string | null
  target: { type: string | null; id: string | null; label: string | null }
  details: Record<string, string | number | boolean | null | Array<string | number | boolean | null>>
}

/** Period is ISO 8601 instants; actor is a username; action matches by prefix. */
export interface AuditFilters {
  since?: string
  until?: string
  actor?: string
  action?: string
  target_type?: string
  target_id?: string
}

export type AuditEventsPage = ItemList<AuditEvent> & { total: number; pages: number; perPage: number }

export function useAuditEventsQuery({
  mine = false,
  page = 1,
  filters = {},
  enabled = true,
}: {
  /** False asks for nothing, for a role the server would refuse. */
  enabled?: boolean
  /** The events that concern the current account, open to every role; the others need the Admin role. */
  mine?: boolean
  page?: number
  filters?: AuditFilters
} = {}) {
  const api = useApi()
  const params = new URLSearchParams()
  for (const [name, value] of Object.entries({ page: page.toString(), ...filters })) {
    if (value) {
      params.set(name, value)
    }
  }
  const qs = params.toString()

  return useQuery<AuditEventsPage>(
    ["audit", mine ? "mine" : "all", qs],
    () => api.fetch(`/audit${mine ? "/mine" : ""}?${qs}`).then((r) => r.json()),
    { enabled },
  )
}
