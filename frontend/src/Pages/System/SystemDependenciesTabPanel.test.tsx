import { renderWithClient } from "tests/utils"
import { expect, it } from "vitest"

import { SystemDependenciesTabPanel } from "./SystemDependenciesTabPanel"

it("renders the title and data when the query is successful", async () => {
  const result = renderWithClient(<SystemDependenciesTabPanel />)

  await result.findByText("numpy")
  expect(result.container).toMatchSnapshot()
})
