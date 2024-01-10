import { useState } from "react"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Filters } from "Types/filters"

import { FiltersSidebar } from "./Components"
import { TransactionDataTable } from "./Components/List"

export function TransactionsListPage() {
  const [filters, setFilters] = useState<Filters>({})
  const [page, setPage] = useState(1)
  const query = useTransactionsListQuery({ filters, page })

  return (
    <Page title="Transactions" description="Explore transactions that went through the proxy">
      <div>
        page
        {[1, 2, 3, 4].map((page) => (
          <a
            href="#"
            onClick={() => {
              setPage(page)
              return false
            }}
          >
            {page}
          </a>
        ))}
      </div>
      <OnQuerySuccess query={query}>
        {(query) => (
          <div className="w-full grid grid-cols-1 grid-rows-1 items-start gap-x-8 gap-y-8 lg:mx-0 lg:max-w-none lg:grid-cols-5">
            <div className="col-start-2 col-span-4 row-end-1">
              <TransactionDataTable transactions={query.data.items} />
            </div>
            <div className="col-start-1 col-span-1">
              <FiltersSidebar filters={filters} setFilters={setFilters} />
            </div>
          </div>
        )}
      </OnQuerySuccess>
    </Page>
  )
}
