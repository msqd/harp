export function truncate(str: string, maxLength: number) {
  if (str.length <= maxLength) {
    return str
  }
  return str.slice(0, maxLength) + "…"
}

export const ucfirst = (s: string) => (s && s[0].toUpperCase() + s.slice(1)) || ""
