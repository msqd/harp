import { ReactNode } from "react"
import tw, { styled } from "twin.macro"

export interface Column<TRow = unknown, TValue = unknown> {
  label: string
  format?: (row: never) => ReactNode
  get?: (row: TRow) => TValue
  onClick?: (row: TRow) => unknown
  className?: string
  headerClassName?: string
}

interface DataTableVariantsProps {
  variant?: "default"
}

type BaseRow = Record<string, unknown>

interface DataTableProps<TRow extends BaseRow, TComputed extends BaseRow> extends DataTableVariantsProps {
  rows: TRow[]
  types: Record<string, Column<TRow>>
  columns?: Array<keyof (TRow & TComputed) | Array<keyof (TRow & TComputed)>>
  onRowClick?: (row: TRow) => unknown
  selected?: TRow
}

const StyledTable = styled.table<DataTableVariantsProps>(() => [tw`min-w-full divide-y divide-gray-300 text-left`])
const StyledTh = styled.th(() => [tw`whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900`])
const StyledTd = styled.td(() => [tw`whitespace-nowrap px-2 py-2 text-sm font-medium text-gray-900`])

function formatRowValue<TRow>(type: Column<TRow>, row: TRow, name: keyof TRow): ReactNode {
  try {
    let value
    if (type.get) {
      value = type.get(row)
    } else {
      value = row[name]
    }

    if (type.format) {
      value = (type.format as (x: unknown) => ReactNode)(value)
    }

    if (!value) {
      return "-"
    }

    return value as ReactNode
  } catch (e) {
    console.error(`Error while rendering value of ${name as string}:\n`, e)
    /* todo warning sign with error in hover ? */
    return "n/a"
  }
}

export function DataTable<TRow extends BaseRow, TComputed extends BaseRow = BaseRow>({
  columns,
  onRowClick,
  rows,
  types,
  variant = "default",
  selected = undefined,
}: DataTableProps<TRow, TComputed>) {
  return (
    <StyledTable variant={variant}>
      <thead>
        <tr>
          {columns?.map((name) => {
            const colName = name as string
            const colType = types[colName]
            return (
              <StyledTh scope="col" key={colName} className={colType.headerClassName ?? ""}>
                {colType.label ?? name}
              </StyledTh>
            )
          })}
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200 bg-white">
        {rows.map((row, index) => {
          return (
            <tr
              key={index}
              onClick={
                onRowClick
                  ? (e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      onRowClick(row)
                    }
                  : undefined
              }
              className={
                "hover:bg-slate-50 cursor-pointer" + (selected && selected.id === row.id ? " bg-slate-100" : "")
              }
            >
              {columns?.map((name, index) => {
                const colName = name as string
                const colType = types[colName]
                const colProps = {} as { onClick?: () => unknown }
                if (colType.onClick !== undefined) {
                  const onClick = colType.onClick
                  colProps["onClick"] = () => onClick(row)
                }
                return (
                  <StyledTd key={index} className={colType.className ?? ""} {...colProps}>
                    {formatRowValue(colType, row, colName)}
                  </StyledTd>
                )
              })}
            </tr>
          )
        })}
      </tbody>
    </StyledTable>
  )
}
