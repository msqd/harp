import { FormEvent, useState } from "react"
import { Helmet } from "react-helmet"

import { OnQuerySuccess, Page, PageTitle } from "Components"
import { AuditFilters, useAuditEventsQuery } from "Domain/Audit"
import { useRole } from "Domain/System"
import { Button } from "ui/Components/Button"
import { Pane } from "ui/Components/Pane"

import { AuditEventsTable } from "./Components/AuditEventsTable.tsx"

import { OptionalPaginator } from "../Transactions/Components/OptionalPaginator.tsx"

/** What the form holds: the period as days, the rest as the API takes it. */
type Draft = Omit<AuditFilters, "since" | "until"> & { from?: string; until?: string }

const FIELDS: { name: keyof Draft; label: string; type?: "date" }[] = [
  { name: "from", label: "From", type: "date" },
  { name: "until", label: "Until", type: "date" },
  { name: "actor", label: "Actor" },
  { name: "action", label: "Action" },
  { name: "target_type", label: "Target type" },
  { name: "target_id", label: "Target id" },
]

/** Days are UTC, the audit's own clock: the whole of the last day is included. */
function toFilters({ from, until, ...rest }: Draft): AuditFilters {
  return {
    ...rest,
    since: from ? `${from}T00:00:00.000Z` : undefined,
    until: until ? `${until}T23:59:59.999Z` : undefined,
  }
}

function AuditFiltersForm({ onApply }: { onApply: (draft: Draft) => void }) {
  const [draft, setDraft] = useState<Draft>({})
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onApply(draft)
  }

  return (
    <form onSubmit={submit} className="mb-4 flex flex-wrap items-end gap-3">
      {FIELDS.map(({ name, label, type }) => (
        <label key={name} className="flex flex-col text-sm font-medium text-gray-900">
          {label}
          <input
            type={type ?? "text"}
            value={draft[name] ?? ""}
            onChange={(event) => setDraft({ ...draft, [name]: event.target.value })}
            className="mt-1 block rounded-md border-0 px-2 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300"
          />
        </label>
      ))}
      <Button>Filter</Button>
    </form>
  )
}

const AuditPage = () => {
  // Asks for nothing until the role is known: the server refuses a role below Admin, so a Viewer must not even try.
  const role = useRole()
  const allowed = role === "admin"
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<AuditFilters>({})
  const query = useAuditEventsQuery({ page, filters, enabled: allowed })

  return (
    <Page title={<PageTitle title="Audit" description="What accounts did to HARP, newest first." />}>
      <Helmet>
        <title>Audit | HARP</title>
        <meta name="description" content="Audit page" />
      </Helmet>
      {role === undefined ? null : !allowed ? (
        <p className="text-sm text-gray-700">The audit needs the Admin role.</p>
      ) : (
        <>
          <AuditFiltersForm
            onApply={(draft) => {
              setFilters(toFilters(draft))
              setPage(1)
            }}
          />
          <OnQuerySuccess query={query}>
            {(query) => (
              <>
                <Pane hasDefaultPadding={false}>
                  <AuditEventsTable events={query.data.items} />
                </Pane>
                <OptionalPaginator
                  current={page}
                  setPage={setPage}
                  total={query.data.total}
                  pages={query.data.pages}
                  perPage={query.data.perPage}
                />
              </>
            )}
          </OnQuerySuccess>
        </>
      )}
    </Page>
  )
}

export default AuditPage
