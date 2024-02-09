import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { ResponseHeading } from "./ResponseHeading"

describe("ResponseHeading", () => {
  test("renders correctly with response", () => {
    const response = {
      summary: "HTTP/1.1 200",
      transaction_id: "1",
      kind: "response",
      headers: "header1:value1\nheader2:value2",
      body: "Foo",
    }

    render(<ResponseHeading response={response} />)

    // Check that the status code and the reason are rendered
    expect(screen.getByText("200 OK")).toBeInTheDocument()
  })
})
