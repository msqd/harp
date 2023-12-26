export type FilterValue = string | number | boolean | undefined
export type Filter = Array<FilterValue> | undefined

export interface Filters extends Record<string, Filter> {}
