import { fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { expect, it, vi } from "vitest"

import { renderWithClient } from "tests/utils"

import { OpenInNewWindowLink } from "./Components/Buttons"
import TransactionDetailPage from "./TransactionDetailPage"

it("gives both transaction link actions readable matching text and preserves copied feedback", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true })
  const result = renderWithClient(
    <MemoryRouter initialEntries={["/transactions/ABCD1234"]}>
      <OpenInNewWindowLink id="ABCD1234" />
      <Routes>
        <Route path="/transactions/:id" element={<TransactionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
  const text = await result.findByText("copy transaction link")
  const control = text.parentElement!
  const openLink = result.getByRole("link", { name: "open in new window" })
  // Tailwind gray-600 is 7.56:1 against the white detail pane (AA requires 4.5:1).
  const sharedClass = [...control.classList].find((name) => name.startsWith("css-"))
  expect(sharedClass).toBeDefined()
  expect(openLink).toHaveClass(sharedClass!)
  const styles = [...document.styleSheets].flatMap((sheet) => [...sheet.cssRules].map((rule) => rule.cssText))
  expect(styles.find((rule) => rule.startsWith(`.${sharedClass} {`))).toContain("color: rgb(75 85 99 /")
  expect(getComputedStyle(control).fontWeight).toBe("500")
  expect(getComputedStyle(openLink).fontWeight).toBe(getComputedStyle(control).fontWeight)

  const originalIcon = control.querySelector("svg")!.innerHTML
  fireEvent.click(text)
  expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/transactions/ABCD1234`)
  await waitFor(() => expect(control.querySelector("svg")!.innerHTML).not.toBe(originalIcon))
  expect(control).toHaveClass(sharedClass!)
})
