import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"
import { MemoryRouter } from "react-router-dom"

import { default as Layout } from "./Layout"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter>
      <Layout />
    </MemoryRouter>,
  )

  await result.findByText("v.test version")
  expect(result.container).toMatchSnapshot()
})
