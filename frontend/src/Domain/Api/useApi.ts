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
    return _fetch(url, { ...(init || {}), method: "POST" })
  }

  /**
   * Wrapper for http delete requests.
   *
   * @param url
   * @param init
   */
  function del(url: string, init?: RequestInit) {
    return _fetch(url, { ...(init || {}), method: "DELETE" })
  }

  return {
    fetch: (url: string) => fetch(urlJoin("/api/", url)),
    get,
    post,
    del,
  }
}
