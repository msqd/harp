export type FilterValue = string | number | boolean | undefined
export type Filter = Array<FilterValue> | "*"

export interface Filters extends Record<string, Filter> {}
