import { ChevronDoubleLeftIcon, ChevronDoubleRightIcon } from "@heroicons/react/16/solid"

interface FiltersVisibilityButtonProps {
  onClick: () => void
}

export function FiltersShowButton({ onClick }: FiltersVisibilityButtonProps) {
  return (
    <button onClick={onClick} className="text-gray-400 mx-1 font-medium text-xs">
      <ChevronDoubleRightIcon className="h-3 w-3 inline-block" />
      <div className="w-4">
        <div className="rotate-90">filters</div>
      </div>
    </button>
  )
}

export function FiltersHideButton({ onClick }: FiltersVisibilityButtonProps) {
  return (
    <button onClick={onClick} className="text-gray-400 mx-1 font-medium text-xs">
      <ChevronDoubleLeftIcon className="h-3 w-3 inline-block" /> hide
    </button>
  )
}
