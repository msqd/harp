import { expect, it } from "vitest"

import { renderWithClient } from "tests/utils"

import { OverviewPage } from "./OverviewPage"
import { MemoryRouter, Route, Routes } from "react-router-dom"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
      </Routes>
    </MemoryRouter>,
  )

  await result.findByText("endpoint1")
  expect(result.container).toMatchSnapshot()
})
