import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { useState } from "react"
import tw, { styled } from "twin.macro"

import { Page } from "Components/Page"
import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess"
import { useTransactionsListQuery } from "Domain/Transactions"
import { Checkbox, Radio } from "mkui/Components/FormWidgets"
import { H5 } from "mkui/Components/Typography"

import { TransactionDataTable } from "./TransactionDataTable.tsx"

const StyledSidebar = styled.aside`
  ${tw`max-w-full w-full divide-y divide-gray-100 overflow-hidden bg-white shadow-sm ring-1 ring-black ring-opacity-5`}
  ${tw`text-gray-900 sm:text-sm`}
`

const endpoints = [{ name: "httpbin" }, { name: "stripe" }, { name: "twilio" }]
const methods = [{ name: "GET" }, { name: "POST" }, { name: "PUT" }, { name: "DELETE" }]
const statuses = [{ name: "2xx" }, { name: "3xx" }, { name: "4xx" }, { name: "5xx" }]
const ratings = [
  { name: "A++" },
  { name: "A+" },
  { name: "A" },
  { name: "B" },
  { name: "C" },
  { name: "D" },
  { name: "E" },
  { name: "F" },
]

function Facet({
  title,
  name,
  values,
  type,
  defaultOpen = true,
}: {
  title: string
  name: string
  values: Array<{ name: string }>
  type: "checkboxes" | "radios"
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="px-4 py-3">
      <fieldset name={name}>
        <H5 as="legend" padding="pt-0" className="flex w-full cursor-pointer" onClick={() => setOpen(!open)}>
          <span className="grow">{title}</span>
          {open ? (
            <ChevronUpIcon className="h-4 w-4 text-gray-600" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 text-gray-600" />
          )}
        </H5>
        <div className={"mt-2 space-y-2 " + (open ? "" : "hidden")}>
          {type === "checkboxes" ? values.map((value) => <Checkbox name={value.name} key={value.name} />) : null}
          {type === "radios" ? values.map((value) => <Radio name={value.name} key={value.name} />) : null}
        </div>
      </fieldset>
    </div>
  )
}

function FiltersSidebar() {
  return (
    <StyledSidebar>
      <input className="h-12 w-full border-0 bg-transparent px-4 focus:ring-0" placeholder="Search..." />
      <Facet title="Endpoint" name="endpoint" values={endpoints} type="checkboxes" />
      <Facet title="Request Method" name="method" values={methods} type="checkboxes" />
      <Facet title="Response Status" name="status" values={statuses} type="checkboxes" />
      <Facet
        title="Period"
        name="period"
        values={[{ name: "Last 24 hours" }, { name: "Last 7 days" }, { name: "Last 15 days" }]}
        type="radios"
      />
      <Facet title="Performance Index" name="tpdex" values={ratings} type="checkboxes" defaultOpen={false} />
    </StyledSidebar>
  )
}

function TransactionsListPage() {
  const query = useTransactionsListQuery()

  return (
    <Page title="Transactions" description="Explore transactions that went through the proxy">
      <OnQuerySuccess query={query}>
        {(query) => (
          <div className="w-full grid grid-cols-1 grid-rows-1 items-start gap-x-8 gap-y-8 lg:mx-0 lg:max-w-none lg:grid-cols-5">
            <div className="col-start-2 col-span-4 row-end-1">
              <TransactionDataTable transactions={query.data.items} />
            </div>
            <div className="col-start-1 col-span-1">
              <FiltersSidebar />
            </div>
          </div>
        )}
      </OnQuerySuccess>
    </Page>
  )
}

export default TransactionsListPage
