import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { TransactionMessagePanel } from "./TransactionMessagePanel"

describe("TransactionMessagePanel", () => {
  test("renders correctly with headers and body", () => {
    const headers = "header1:value1\nheader2:value2"
    const body = "Foo"
    const contentType = "application/json"

    render(<TransactionMessagePanel messageId={"1"} headers={headers} body={body} contentType={contentType} />)

    // Check that the headers are rendered
    headers.split("\n").forEach((line) => {
      const [header, value] = line.split(":")
      expect(screen.getByText(header)).toBeInTheDocument()
      expect(screen.getByText(value)).toBeInTheDocument()
    })

    // Check that the body is rendered
    expect(screen.getByText(body)).toBeInTheDocument()

    // Check that the content type is rendered
    expect(screen.getByText(`Body (${contentType})`)).toBeInTheDocument()
  })

  test("renders correctly without headers and body", () => {
    render(<TransactionMessagePanel messageId={"2"} />)

    // Check that the headers title is rendered
    expect(screen.getByText("Headers")).toBeInTheDocument()

    // Check that the body title is rendered
    expect(screen.getByText("Body")).toBeInTheDocument()

    // Check that no headers or body are rendered
    expect(screen.queryByRole("row")).toBeNull()
  })
})
