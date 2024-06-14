export type FilterValue = string | number | boolean | undefined

export type MinMaxFilter = {
  min?: number
  max?: number
}

export type Filter = Array<FilterValue> | MinMaxFilter | undefined
export type ArrayFilter = Array<FilterValue> | undefined
export interface Filters extends Record<string, Filter> {}
