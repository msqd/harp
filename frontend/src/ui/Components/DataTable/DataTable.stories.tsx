import { DataTable } from "./DataTable"

interface TRow {
  firstName: string
  lastName: string
  instrument: string
  country: string
}

export const Default = () => (
  <DataTable
    types={{
      firstName: { label: "First name" },
      lastName: { label: "Last name" },
      instrument: { label: "Instrument" },
      country: { label: "Country" },
    }}
    columns={["firstName", "lastName", "instrument", "country"]}
    rows={
      [
        { firstName: "John", lastName: "Coltrane", instrument: "Saxophone", country: "USA" },
        { firstName: "Miles", lastName: "Davis", instrument: "Trumpet", country: "USA" },
        { firstName: "Thelonious", lastName: "Monk", instrument: "Piano", country: "USA" },
        { firstName: "Charles", lastName: "Mingus", instrument: "Double Bass", country: "USA" },
      ] as TRow[]
    }
  />
)
