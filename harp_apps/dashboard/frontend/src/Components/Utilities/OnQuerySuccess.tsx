import { ReactElement } from "react"
import { useErrorBoundary } from "react-error-boundary"
import { UseQueryResult } from "react-query"
import { QueryObserverSuccessResult } from "react-query/types/core/types"

interface OnQuerySuccessCommonProps<T> {
  children: (...queries: QueryObserverSuccessResult<T>[]) => ReactElement
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

function OnQuerySuccess<T>(props: OnQuerySuccessProps<T> | OnQueriesSuccessProps<T>) {
  const queries = "query" in props ? [props.query] : props.queries

  const { showBoundary } = useErrorBoundary()

  if (anyQueryIsLoading(queries)) {
    return <div>Loading...</div>
  }

  if (anyQueryIsError(queries) || anyQueryIsNotSuccess(queries)) {
    showBoundary(new Error("Error while loading required remote data!"))
    return null
  }

  return props.children(...(queries as QueryObserverSuccessResult<T>[]))
}

export { OnQuerySuccess }
