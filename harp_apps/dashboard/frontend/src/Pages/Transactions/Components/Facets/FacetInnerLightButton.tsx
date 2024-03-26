interface FacetInnerLightButtonProps {
  label: string
  handler: () => unknown
}

export function FacetInnerLightButton({ label, handler }: FacetInnerLightButtonProps) {
  return (
    <button
      className="text-gray-400 mx-1 font-medium text-xs"
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        handler()
      }}
    >
      {label}
    </button>
  )
}
