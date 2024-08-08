declare namespace Settings.Proxy {
  // proxy.endpoints: [...]
  export interface Endpoint {
    name: string
    port: number
    description: string
    remote: Remote
  }

  // proxy.endpoints[].remote: ...
  interface Remote {
    endpoints: RemoteEndpoint[]
    min_pool_size?: number
    probe?: Probe
    current_pool?: string[]
    break_on?: string[]
  }

  // proxy.endpoints[].remote.endpoints: [...]
  export interface RemoteEndpoint {
    url: string
    failure_threshold?: number
    success_threshold?: number
    pools?: string[]
    status?: "up" | "checking" | "down" | "unknown"
  }

  // proxy.endpoints[].remote.probe: ...
  export interface HttpProbe {
    type: "http"
    method: string
    path: string
    headers?: Record<string, string>
    timeout?: number
  }
  export type Probe = HttpProbe
}
