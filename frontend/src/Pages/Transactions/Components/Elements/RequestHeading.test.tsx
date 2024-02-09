import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { RequestHeading } from "./RequestHeading"

describe("RequestHeading", () => {
  test("renders correctly with request and endpoint", () => {
    const endpoint = "endpoint1"
    const request = {
      transaction_id: "1",
      summary: "GET /path",
      kind: "request",
      headers: "header1:value1\nheader2:value2",
      body: "Foo",
    }

    render(<RequestHeading endpoint={endpoint} request={request} />)

    // Check that the endpoint is rendered
    expect(screen.getByText(endpoint)).toBeInTheDocument()

    // Check that the method is rendered
    expect(screen.getByText("GET")).toBeInTheDocument()

    // Check that the url is rendered
    expect(screen.getByText("/path")).toBeInTheDocument()
  })

  test("renders correctly without request and endpoint", () => {
    render(<RequestHeading />)

    // Check that the n/a text is rendered
    expect(screen.getByText("n/a")).toBeInTheDocument()
  })
})
