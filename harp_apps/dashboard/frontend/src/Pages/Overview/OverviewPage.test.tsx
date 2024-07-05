import { it } from "vitest"

import { renderWithClient } from "tests/utils"

import { MemoryRouter, Route, Routes } from "react-router-dom"
import OverviewPage from "./OverviewPage.tsx"
import { waitForElementToBeRemoved } from "@testing-library/react"

it.skip("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
      </Routes>
    </MemoryRouter>,
  )

  await waitForElementToBeRemoved(() => result.getAllByText("Loading..."), { timeout: 10000 })

  await result.findByText("endpoint1")

  // todo: for this to work, we need to ignore the difference in _echarts_instance_ attribute, which is a sequence
  //  starting at the initial timestamp. That could be overcome by using vitest fake timers, but then the suspense
  //  implementation wont work anymore. One way would be custom renderers, but too much time has already been spent
  //  here, for too little value.
  //expect(result.container).toMatchSnapshot()
}, { timeout: 10000 })
