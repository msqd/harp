import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { KeyValueSettings, Setting } from "Domain/System/useSystemSettingsQuery"

import { SettingsTable } from "./SettingsTable"

describe("SettingsTable", () => {
  test("renders correctly with settings", () => {
    const settings = {
      key1: "value1",
      key2: 123,
      key3: true,
      key4: false,
      key5: null,
      key6: {
        key7: "value7",
        key8: 456,
      },
    }

    render(<SettingsTable settings={settings} />)

    // Recursive function to check keys and values
    const checkSettings = (settings: KeyValueSettings | Array<Setting>) => {
      Object.entries(settings).forEach(([key, value]) => {
        // Check that the key is rendered
        expect(screen.getByText(key)).toBeInTheDocument()

        // Check the value
        if (value === null) {
          expect(screen.getByText("null")).toBeInTheDocument()
        } else if (typeof value === "boolean") {
          expect(screen.getByText(value.toString())).toBeInTheDocument()
        } else if (typeof value === "object") {
          // Recursively check nested settings
          checkSettings(value)
        } else {
          expect(screen.getByText(value.toString())).toBeInTheDocument()
        }
      })
    }

    // Check the settings
    checkSettings(settings)
  })

  test("renders correctly with empty settings", () => {
    render(<SettingsTable settings={{}} />)

    // Check that no table rows are rendered
    expect(screen.queryByRole("row")).toBeNull()
  })
})
