import { AuditEvent } from "Domain/Audit"
import { Badge, BadgeColor } from "ui/Components/Badge"
import { Column, DataTable } from "ui/Components/DataTable"

const OUTCOME_COLORS: Record<AuditEvent["outcome"], BadgeColor> = {
  succeeded: "green",
  failed: "orange",
  denied: "red",
}

type Row = {
  id: number
  occurredAt: string
  action: string
  outcome: AuditEvent["outcome"]
  actor: string
  target: string
  origin: string
  details: string
}

const toRow = (event: AuditEvent): Row => ({
  id: event.id,
  occurredAt: event.occurredAt,
  action: event.action,
  outcome: event.outcome,
  actor: event.actor.label ?? (event.actor.id === null ? "system" : `#${event.actor.id}`),
  target: [event.target.type, event.target.label ?? event.target.id].filter(Boolean).join(" "),
  origin: event.ip ?? "",
  details: Object.entries(event.details)
    .map(([name, value]) => `${name}: ${String(value)}`)
    .join(", "),
})

const types: Record<keyof Row, Column<Row>> = {
  id: { label: "#" },
  occurredAt: {
    label: "When",
    format: ((value: string) => <time dateTime={value}>{new Date(value).toLocaleString()}</time>) as never,
  },
  action: { label: "Action", className: "font-mono" },
  outcome: {
    label: "Outcome",
    format: ((value: AuditEvent["outcome"]) => <Badge color={OUTCOME_COLORS[value]}>{value}</Badge>) as never,
  },
  actor: { label: "Actor" },
  target: { label: "Target" },
  origin: { label: "From" },
  details: { label: "Details", className: "text-gray-500 font-normal" },
}

/** The events as the API sends them (newest first), the ones the account may see and nothing else. */
export function AuditEventsTable({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return <p className="py-4 text-sm text-gray-700">No activity yet.</p>
  }
  return (
    <DataTable<Row>
      rows={events.map(toRow)}
      types={types}
      columns={["occurredAt", "action", "outcome", "actor", "target", "origin", "details"]}
    />
  )
}
