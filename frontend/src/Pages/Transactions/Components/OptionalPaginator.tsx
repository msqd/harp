import { Paginator } from "ui/Components/Pagination"

export function OptionalPaginator({
  current,
  setPage,
  total,
  pages,
  perPage,
}: {
  current: number
  setPage: (page: number) => void
  total?: number
  pages?: number
  perPage?: number
}) {
  const paginatorProps = {
    current,
    setPage,
    total: total ?? undefined,
    pages: pages ?? undefined,
    perPage: perPage ?? undefined,
  }

  return (paginatorProps.total || 0) > 0 ? <Paginator {...paginatorProps} showSummary={false} /> : null
}
