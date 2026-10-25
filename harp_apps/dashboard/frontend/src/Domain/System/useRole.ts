import { useSystemQuery } from "./useSystemQuery.ts"

export type Role = "viewer" | "editor" | "admin"

const ROLES: Role[] = ["viewer", "editor", "admin"]

/**
 * Whether `role` may do what `required` allows. A role that is not known yet (the system query is still loading)
 * hides nothing: what is hidden is a courtesy, the server answers 403 to what a role may not do.
 */
export function roleIncludes(role: Role | undefined, required: Role): boolean {
  return role === undefined || ROLES.indexOf(role) >= ROLES.indexOf(required)
}

/** The role the current request acts with, undefined until known. */
export function useRole(): Role | undefined {
  return useSystemQuery().data?.role
}

export function useCan(required: Role): boolean {
  return roleIncludes(useRole(), required)
}
