export function FacetLabel({ name, count = undefined }: { name: string; count?: number }) {
  return (
    <div>
      {name}
      {count ? <span className={"text-xs text-gray-400"}> ({count})</span> : null}
    </div>
  )
}
