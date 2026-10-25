import { useState } from "react"
import { Helmet } from "react-helmet"

import { OnQuerySuccess, Page, PageTitle } from "Components"
import { useAuditEventsQuery } from "Domain/Audit"
import { AuditEventsTable } from "Pages/Audit/Components/AuditEventsTable.tsx"
import { Pane } from "ui/Components/Pane"
import { H2 } from "ui/Components/Typography"

import { OptionalPaginator } from "../Transactions/Components/OptionalPaginator.tsx"

/** What this account did and what was done to it: a sign-in, a session or a token you do not know shows here. */
const AccountPage = () => {
  const [page, setPage] = useState(1)
  const query = useAuditEventsQuery({ mine: true, page })

  return (
    <Page title={<PageTitle title="My account" description="What concerns your account." />}>
      <Helmet>
        <title>My account | HARP</title>
        <meta name="description" content="My account page" />
      </Helmet>
      <H2>My activity</H2>
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
    </Page>
  )
}

export default AccountPage
