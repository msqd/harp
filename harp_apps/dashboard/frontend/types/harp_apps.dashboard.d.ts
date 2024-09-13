/* eslint-disable */
/**
 * This file was automatically generated by json-schema-to-typescript.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source JSONSchema file,
 * and run json-schema-to-typescript to regenerate this file.
 */

declare namespace Apps.Dashboard {
  export interface DevserverSettings {
    enabled?: boolean;
    port?: number | null;
  }
  export interface BasicAuthSettings {
    type?: "basic";
    algorithm?:
      | "argon2"
      | "bcrypt"
      | "bcrypt_sha256"
      | "cisco_asa"
      | "cisco_pix"
      | "cisco_type7"
      | "django_bcrypt"
      | "django_bcrypt_sha256"
      | "django_des_crypt"
      | "django_disabled"
      | "django_pbkdf2_sha1"
      | "django_pbkdf2_sha256"
      | "django_salted_md5"
      | "django_salted_sha1"
      | "grub_pbkdf2_sha512"
      | "hex_digest"
      | "ldap_crypt"
      | "ldap_md5"
      | "ldap_plaintext"
      | "ldap_salted_md5"
      | "ldap_salted_sha1"
      | "ldap_salted_sha256"
      | "ldap_salted_sha512"
      | "ldap_sha1"
      | "lmhash"
      | "md5_crypt"
      | "msdcc"
      | "msdcc2"
      | "mssql2000"
      | "mssql2005"
      | "mysql323"
      | "mysql41"
      | "nthash"
      | "oracle10"
      | "oracle11"
      | "pbkdf2_sha1"
      | "pbkdf2_sha256"
      | "pbkdf2_sha512"
      | "phpass"
      | "plain"
      | "plaintext"
      | "postgres_md5"
      | "scram"
      | "scrypt"
      | "sha256_crypt"
      | "sha512_crypt";
    users?: Users;
  }
  export interface Users {
    [k: string]: User;
  }
  export interface User {
    password: string;
  }
  /**
   * Root settings for the dashboard application.
   */
  export interface DashboardSettings {
    port?: number;
    auth?: BasicAuthSettings;
    devserver?: DevserverSettings | null;
    enable_ui?: boolean;
    public_url?: string | null;
  }
  export interface SystemPutProxyInput {
    endpoint: string;
    action: "up" | "down" | "checking";
    url: string;
    [k: string]: unknown;
  }
}