/* eslint-disable */
/**
 * This file was automatically generated by json-schema-to-typescript.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source JSONSchema file,
 * and run json-schema-to-typescript to regenerate this file.
 */

declare namespace Apps.Storage {
  export interface DatabaseSettings {
    url?: string;
  }
  export interface StorageSettings {
    url?: string;
    migrate?: boolean;
    blobs?: BlobStorageSettings;
    redis?: RedisSettings | null;
  }
  export interface BlobStorageSettings {
    /**
     * Base type for service definition.
     */
    base?: string | null;
    type?: "sql" | "redis";
    /**
     * Optional custom constructor for the service.
     */
    constructor?: string | null;
    /**
     * Arguments for the service constructor.
     */
    arguments?: {
      [k: string]: unknown;
    } | null;
    [k: string]: unknown;
  }
  export interface RedisSettings {
    /**
     * Base type for service definition.
     */
    base?: string | null;
    /**
     * Type for service definition.
     */
    type?: string | null;
    /**
     * Optional custom constructor for the service.
     */
    constructor?: string | null;
    /**
     * Arguments for the service constructor.
     */
    arguments?: {
      [k: string]: unknown;
    } | null;
    url?: string;
    [k: string]: unknown;
  }
}