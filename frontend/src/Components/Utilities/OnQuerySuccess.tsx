import { ReactElement } from "react";
import { UseQueryResult } from "react-query";
import { QueryObserverSuccessResult } from "react-query/types/core/types";

interface OnQuerySuccessProps<T> {
  query: UseQueryResult<T>;
  children: (query: QueryObserverSuccessResult<T>) => ReactElement;
}

function OnQuerySuccess<T>({ query, children }: OnQuerySuccessProps<T>) {
  if (query.isLoading) {
    return <div>Loading...</div>;
  }

  if (query.isError || !query.isSuccess) {
    return <div>Error!</div>;
  }

  return children(query);
}

export { OnQuerySuccess };
