import tw, { styled } from "twin.macro"
import { ReactNode } from "react"

export interface Column<TRow = any, TValue = any> {
  label: string
  format?: (x: TValue) => ReactNode
  get?: (row: TRow) => TValue
  onClick?: (row: TRow) => unknown
  className?: string
  headerClassName?: string
}

interface DataTableVariantsProps {
  variant?: "default"
}

interface DataTableProps<TRow extends Record<string, any>, TComputed extends Record<string, any>>
  extends DataTableVariantsProps {
  rows: TRow[]
  types: Record<string, Column<TRow>>
  columns?: Array<keyof (TRow & TComputed) | Array<keyof (TRow & TComputed)>>
  onRowClick?: (row: TRow) => unknown
}

const StyledTable = styled.table(({}: DataTableVariantsProps) => [tw`min-w-full divide-y divide-gray-300 text-left`])
const StyledTh = styled.th(() => [tw`whitespace-nowrap px-2 py-3.5 text-left text-sm font-semibold text-gray-900`])
const StyledTd = styled.td(() => [tw`whitespace-nowrap px-2 py-2 text-sm font-medium text-gray-900`])

function formatRowValue<TRow>(type: Column<TRow>, row: TRow, name: keyof TRow): ReactNode {
  let value
  if (type.get) {
    value = type.get(row)
  } else {
    value = row[name]
  }

  if (type.format) {
    return type.format(value)
  }

  return value as ReactNode
}

type BaseRow = Record<string, any>

export function DataTable<TRow extends BaseRow, TComputed extends BaseRow = {}>({
  columns,
  onRowClick,
  rows,
  types,
  variant = "default",
}: DataTableProps<TRow, TComputed>) {
  return (
    <StyledTable variant={variant}>
      <thead>
        <tr>
          {columns?.map((name) => {
            const colName = name as string
            const colType = types[colName]
            return (
              <StyledTh
                scope="col"
                key={colName}
                className={colType.headerClassName ?? ""}
              >
                {colType.label ?? name}
              </StyledTh>
            )
          })}
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200 bg-white">
        {rows.map((row, index) => {
          return (
            <tr key={index} onClick={onRowClick ? () => onRowClick(row) : undefined}>
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
