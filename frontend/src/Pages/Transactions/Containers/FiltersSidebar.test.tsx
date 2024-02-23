import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"
import { FiltersSidebar } from "./FiltersSidebar"
import { describe } from "node:test"
import { Filters } from "Types/filters"

const filters: Filters = {}

const setFilters = (filters: Filters) => {
  return filters
}
describe("FiltersSidebar", () => {
  it("renders the title and data when the query is successful", async () => {
    const result = renderWithClient(<FiltersSidebar filters={filters} setFilters={setFilters} />)

    await result.findByText("Request Method")
    expect(result.container).toMatchSnapshot()
  })
})
