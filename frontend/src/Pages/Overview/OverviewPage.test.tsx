import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"

import { OverviewPage } from "./OverviewPage"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(<OverviewPage />)

  await result.findByText("endpoint1")
  expect(result.container).toMatchSnapshot()
})
