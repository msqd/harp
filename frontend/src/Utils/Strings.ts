export function isUrl(urlOrWhatever: string) {
  let url

  try {
    url = new URL(urlOrWhatever)
  } catch (_) {
    return false
  }

  return url.protocol === "http:" || url.protocol === "https:"
}

export function truncate(str: string, maxLength: number) {
  if (str.length <= maxLength) {
    return str
  }
  return str.slice(0, maxLength) + "…"
}
