/* eslint-disable */
/**
 * This file was automatically generated by json-schema-to-typescript.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source JSONSchema file,
 * and run json-schema-to-typescript to regenerate this file.
 */

declare namespace Apps.Proxy {
  export interface BaseProxySettings {}
  export interface Proxy {
    settings: ProxySettings;
    [k: string]: unknown;
  }
  /**
   * Configuration parser for ``proxy`` settings.
   *
   * .. code-block:: yaml
   *
   *     endpoints:
   *       # see ProxyEndpoint
   *       - ...
   */
  export interface ProxySettings {
    endpoints?: EndpointSettings[];
  }
  /**
   * Configuration parser for ``proxy.endpoints[]`` settings.
   *
   * .. code-block:: yaml
   *
   *     name: my-endpoint
   *     port: 8080
   *     description: My endpoint
   *     remote:
   *       # see HttpRemote
   *       ...
   *
   * A shorthand syntax is also available for cases where you only need to proxy to a single URL and do not require
   * fine-tuning the endpoint settings:
   *
   * .. code-block:: yaml
   *
   *     name: my-endpoint
   *     port: 8080
   *     description: My endpoint
   *     url: http://my-endpoint:8080
   */
  export interface EndpointSettings {
    name: string;
    port: number;
    description?: string | null;
    remote?: RemoteSettings | null;
  }
  /**
   * A ``HttpRemote`` is a collection of endpoints that a proxy will use to route requests. It is used as the
   * configuration parser for ``proxy.endpoints[].remote`` settings.
   *
   * .. code-block:: yaml
   *
   *     min_pool_size: 1
   *     endpoints:
   *       # see HttpEndpoint
   *       - ...
   *     probe:
   *       # see HttpProbe
   *       ...
   */
  export interface RemoteSettings {
    min_pool_size?: number;
    break_on?: unknown[];
    check_after?: number;
    endpoints?: RemoteEndpointSettings[];
    probe?: RemoteProbeSettings | null;
  }
  /**
   * A ``HttpEndpoint`` is an instrumented target URL that a proxy will use to route requests. It is used as the
   * configuration parser for ``proxy.endpoints[].remote.endpoints[]`` settings.
   *
   * .. code-block:: yaml
   *
   *     url: "http://my-endpoint:8080"
   *     pools: [fallback]  # omit for default pool
   *     failure_threshold: 3
   *     success_threshold: 1
   */
  export interface RemoteEndpointSettings {
    url: string;
    pools?: string[];
    failure_threshold?: number;
    success_threshold?: number;
  }
  /**
   * A ``HttpProbe`` is a health check that can be used to check the health of a remote's endpoints. It is used as the
   * configuration parser for ``proxy.endpoints[].remote.probe`` settings.
   *
   * .. code-block:: yaml
   *
   *     type: http
   *     method: GET
   *     path: /health
   *     headers:
   *       x-purpose: "health probe"
   *     timeout: 5.0
   */
  export interface RemoteProbeSettings {
    method?: string;
    path?: string;
    headers?: Headers;
    interval?: string;
    timeout?: string;
    verify?: boolean;
  }
  export interface Headers {
    [k: string]: unknown;
  }
  export interface BaseEndpointSettings {
    name: string;
    port: number;
    description?: string | null;
  }
  export interface Endpoint {
    settings: EndpointSettings;
    remote?: Remote;
    [k: string]: unknown;
  }
  export interface Remote {
    settings: RemoteSettings;
    current_pool_name?: string;
    probe?: RemoteProbe | null;
    current_pool: string[];
    endpoints: RemoteEndpoint[];
    [k: string]: unknown;
  }
  /**
   * Stateful version of a probe definition.
   */
  export interface RemoteProbe {
    settings: RemoteProbeSettings;
    [k: string]: unknown;
  }
  /**
   * Stateful version of a remote endpoint definition.
   */
  export interface RemoteEndpoint {
    settings: RemoteEndpointSettings;
    status?: number;
    failure_score?: number;
    success_score?: number;
    failure_reasons?: unknown[] | null;
    [k: string]: unknown;
  }
  export interface BaseRemoteSettings {
    min_pool_size?: number;
    break_on?: unknown[];
    check_after?: number;
  }
}