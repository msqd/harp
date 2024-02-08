import { render, fireEvent } from "@testing-library/react"
import { DataTable, Column } from "./DataTable"

describe("DataTable", () => {
  const types: Record<string, Column> = {
    firstName: { label: "First name" },
    lastName: { label: "Last name" },
    instrument: { label: "Instrument" },
    country: { label: "Country" },
  }

  const columns = ["firstName", "lastName", "instrument", "country"]
  const rows = [
    { firstName: "John", lastName: "Coltrane", instrument: "Saxophone", country: "USA" },
    { firstName: "Miles", lastName: "Davis", instrument: "Trumpet", country: "USA" },
    { firstName: "Thelonious", lastName: "Monk", instrument: "Piano", country: "USA" },
    { firstName: "Charles", lastName: "Mingus", instrument: "Double Bass", country: "USA" },
  ]
  it("renders correctly", () => {
    const { asFragment } = render(<DataTable types={types} columns={columns} rows={rows} />)
    expect(asFragment()).toMatchSnapshot()
  })

  it("renders the table headers", () => {
    const { getByText } = render(<DataTable types={types} columns={columns} rows={rows} />)

    expect(getByText("First name")).toBeInTheDocument()
    expect(getByText("Last name")).toBeInTheDocument()
    expect(getByText("Instrument")).toBeInTheDocument()
    expect(getByText("Country")).toBeInTheDocument()
  })

  it("renders the table rows", () => {
    const { getByText, getAllByText } = render(<DataTable types={types} columns={columns} rows={rows} />)

    expect(getByText("John")).toBeInTheDocument()
    expect(getByText("Coltrane")).toBeInTheDocument()
    expect(getByText("Saxophone")).toBeInTheDocument()
    expect(getByText("Miles")).toBeInTheDocument()
    expect(getByText("Davis")).toBeInTheDocument()
    expect(getByText("Trumpet")).toBeInTheDocument()
    expect(getAllByText("USA").length).toBe(4)
  })

  it("calls onRowClick when a row is clicked", () => {
    const onRowClick = jest.fn()
    const { getByText } = render(<DataTable types={types} columns={columns} rows={rows} onRowClick={onRowClick} />)

    fireEvent.click(getByText("John"))
    expect(onRowClick).toHaveBeenCalledWith(rows[0])
  })
  it("uses provided get function", () => {
    const getfn = jest.fn((row: (typeof rows)[0]) => row.firstName)

    const types: Record<string, Column> = {
      firstName: { label: "First name", get: getfn },
      lastName: { label: "Last name" },
      instrument: { label: "Instrument" },
      country: { label: "Country" },
    }

    render(<DataTable types={types} columns={columns} rows={rows} />)

    rows.forEach((row) => {
      expect(getfn).toHaveBeenCalledWith(row)
    })
  })

  it("uses provided format function", () => {
    const formatfn = jest.fn((firstName: string) => firstName)

    const types: Record<string, Column> = {
      firstName: { label: "First name", format: formatfn },
      lastName: { label: "Last name" },
      instrument: { label: "Instrument" },
      country: { label: "Country" },
    }

    render(<DataTable types={types} columns={columns} rows={rows} />)

    rows.forEach((row) => {
      expect(formatfn).toHaveBeenCalledWith(row.firstName)
    })
  })

  it("shows - when no value", () => {
    const rows = [{ firstName: "Charles", lastName: "Mingus", instrument: "Double Bass" }]

    const { getByText } = render(<DataTable types={types} columns={columns} rows={rows} />)

    expect(getByText("-")).toBeInTheDocument()
  })
  it("allows specific onClick actions for column", () => {
    const onClick = jest.fn()
    const types: Record<string, Column> = {
      firstName: { label: "First name", onClick },
      lastName: { label: "Last name" },
      instrument: { label: "Instrument" },
      country: { label: "Country" },
    }

    const { getByText } = render(<DataTable types={types} columns={columns} rows={rows} />)

    fireEvent.click(getByText("John"))
    expect(onClick).toHaveBeenCalledWith(rows[0])
  })

  it("handles errors in get or format function and shows n/a", () => {
    const getfn = jest.fn(() => {
      throw new Error("test")
    })

    const types: Record<string, Column> = {
      firstName: { label: "First name", get: getfn },
      lastName: { label: "Last name" },
      instrument: { label: "Instrument" },
      country: { label: "Country" },
    }

    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {})

    const { getAllByText } = render(<DataTable types={types} columns={columns} rows={rows} />)

    expect(getAllByText("n/a").length).toBe(4)
    consoleErrorSpy.mockRestore()
  })
})
