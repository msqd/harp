import urlJoin from "url-join"

export function useApi() {
  return {
    fetch: (url: string) => fetch(urlJoin("/api/", url)),
  }
}
