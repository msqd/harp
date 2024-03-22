import { ChevronDoubleLeftIcon, ChevronDoubleRightIcon, XMarkIcon } from "@heroicons/react/16/solid"

interface PaneVisibilityButtonProps {
  onClick: () => void
}

export function FiltersShowButton({ onClick }: PaneVisibilityButtonProps) {
  return (
    <button onClick={onClick} className="text-gray-400 mx-1 font-medium text-xs">
      <ChevronDoubleRightIcon className="h-3 w-3 inline-block" />
      <div className="w-4">
        <div className="rotate-90">filters</div>
      </div>
    </button>
  )
}

export function FiltersHideButton({ onClick }: PaneVisibilityButtonProps) {
  return (
    <button onClick={onClick} className="text-gray-400 mx-1 font-medium text-xs">
      <ChevronDoubleLeftIcon className="h-3 w-3 inline-block" /> hide
    </button>
  )
}

export function DetailsCloseButton({ onClick }: PaneVisibilityButtonProps) {
  return (
    <button onClick={onClick} className="text-gray-400 mx-1 font-medium text-xs">
      <XMarkIcon className="h-3 w-3 inline-block" /> close
    </button>
  )
}
