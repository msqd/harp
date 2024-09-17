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

function anyQueryIsNotSuccess<T>(queries: UseQueryResult<T>[]): boolean {
  return queries.some((query) => !query.isSuccess)
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

  if (anyQueryIsError(queries) || anyQueryIsNotSuccess(queries)) {
    showBoundary(new Error("Error while loading required remote data!"))
    return null
  }

  return props.children(...(queries as QueryObserverSuccessResult<T>[]))
}
