import { render, screen } from "@testing-library/react"
import { expect, describe, it } from "vitest"

import { Tab } from "./Tabs"

describe("Tab", () => {
  it("renders correctly", () => {
    const { container } = render(
      <Tab.Group>
        <Tab.List>
          <Tab>Tab 1</Tab>
        </Tab.List>
        <Tab.Panels>
          <Tab.Panel>Panel 1</Tab.Panel>
        </Tab.Panels>
      </Tab.Group>,
    )
    expect(container).toMatchSnapshot()
  })

  it("renders without crashing", () => {
    const { container } = render(
      <Tab.Group>
        <Tab.List>
          <Tab>Tab 1</Tab>
        </Tab.List>
        <Tab.Panels>
          <Tab.Panel>Panel 1</Tab.Panel>
        </Tab.Panels>
      </Tab.Group>,
    )
    expect(container.firstChild).toBeTruthy()
  })

  it("renders the correct content", () => {
    render(
      <Tab.Group>
        <Tab.List>
          <Tab>Tab 1</Tab>
        </Tab.List>
        <Tab.Panels>
          <Tab.Panel>Panel 1</Tab.Panel>
        </Tab.Panels>
      </Tab.Group>,
    )
    expect(screen.getByText("Tab 1")).toBeInTheDocument()
    expect(screen.getByText("Panel 1")).toBeInTheDocument()
  })
})
