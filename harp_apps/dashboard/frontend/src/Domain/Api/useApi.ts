import urlJoin from "url-join"

export function useApi() {
  /**
   * Raw fetch wrapper, embedding authentication and common parameters into init.
   *
   * @param path
   * @param init
   */
  function _fetch(url: string, init?: RequestInit) {
    return fetch(urlJoin("/api/", url), {
      ...(init || {}),
    })
  }

  /**
   * State-changing requests always declare JSON: the API refuses anything else, which a cross-site form cannot send.
   */
  function _fetchJson(url: string, init: RequestInit | undefined, method: string) {
    const headers = new Headers(init?.headers)
    headers.set("Content-Type", "application/json")
    return _fetch(url, { ...(init || {}), method, headers })
  }

  /**
   * Wrapper for http get requests.
   *
   * @param url
   * @param init
   */
  function get(url: string, init?: RequestInit) {
    return _fetch(url, { ...(init || {}), method: "GET" })
  }

  /**
   * Wrapper for http post requests.
   *
   * @param url
   * @param init
   */
  function post(url: string, init?: RequestInit) {
    return _fetchJson(url, init, "POST")
  }

  /**
   * Wrapper for http delete requests.
   *
   * @param url
   * @param init
   */
  function del(url: string, init?: RequestInit) {
    return _fetchJson(url, init, "DELETE")
  }

  /**
   * Wrapper for http delete requests.
   *
   * @param url
   * @param init
   */
  function put(url: string, init?: RequestInit) {
    return _fetchJson(url, init, "PUT")
  }

  return {
    fetch: (url: string) => fetch(urlJoin("/api/", url)),
    get,
    post,
    del,
    put,
  }
}
