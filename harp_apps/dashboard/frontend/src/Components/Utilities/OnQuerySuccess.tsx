import { ReactElement, ReactNode } from "react"
import { useErrorBoundary } from "react-error-boundary"
import { UseQueryResult } from "react-query"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

interface OnQuerySuccessCommonProps<T> {
  children: (...queries: QueryObserverSuccessResult<T>[]) => ReactElement
  onQueryError?: () => void
}

interface OnQuerySuccessProps<T> extends OnQuerySuccessCommonProps<T> {
  query: UseQueryResult<T>
}

interface OnQueriesSuccessProps<T> extends OnQuerySuccessCommonProps<T> {
  queries: UseQueryResult<T>[]
}

function anyQueryIsLoading<T>(queries: UseQueryResult<T>[]): boolean {
  return queries.some((query) => query.isLoading)
}

function anyQueryIsError<T>(queries: UseQueryResult<T>[]): boolean {
  return queries.some((query) => query.isError)
}

function hasUsableData<T>(query: UseQueryResult<T>): boolean {
  // A failed refetch keeps the previous data: it is still worth showing.
  return query.isSuccess || (query.isError && query.data !== undefined)
}

function anyQueryHasNoUsableData<T>(queries: UseQueryResult<T>[]): boolean {
  return queries.some((query) => !hasUsableData(query))
}

export function OnQuerySuccess<T>(
  props: (OnQuerySuccessProps<T> | OnQueriesSuccessProps<T>) & { fallback?: ReactNode },
) {
  const queries = "query" in props ? [props.query] : props.queries

  const { showBoundary } = useErrorBoundary()

  if (anyQueryIsError(queries)) {
    if (props?.onQueryError) {
      props.onQueryError()
    }
  }

  if (anyQueryIsLoading(queries)) {
    return props.fallback ?? <div>Loading...</div>
  }

  if (anyQueryHasNoUsableData(queries)) {
    showBoundary(new Error("Error while loading required remote data!"))
    return null
  }

  const content = props.children(...(queries as QueryObserverSuccessResult<T>[]))

  if (!anyQueryIsError(queries)) {
    return content
  }

  return (
    <>
      <div
        role="status"
        className="mb-2 rounded border border-yellow-400 bg-yellow-50 px-3 py-2 text-sm text-yellow-800"
      >
        Data could not be refreshed, showing the last loaded version. Retrying automatically.
      </div>
      {content}
    </>
  )
}
