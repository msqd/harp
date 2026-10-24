import { expect, it } from "vitest"

import { Filters } from "Types/filters"
import { renderWithClient } from "tests/utils"

import { FiltersSidebar } from "./FiltersSidebar"
import { MemoryRouter } from "react-router"

const filters: Filters = {}

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter>
      <FiltersSidebar filters={filters} />
    </MemoryRouter>,
  )
  await result.findByText("Request Method")
  expect(result.container).toMatchSnapshot()
})
