import { useRef } from "react"

interface SearchBarProps {
  label?: string
  placeHolder?: string
  setSearch?: (value: string) => void
  className?: string
}

export const SearchBar = ({ label, setSearch, className, placeHolder }: SearchBarProps) => {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (setSearch) {
        setSearch(e.currentTarget.value)
      }
    }
  }

  const handleSearchClick = () => {
    if (inputRef.current) {
      if (setSearch) {
        setSearch(inputRef.current.value)
      }
    }
  }

  return (
    <div className={className}>
      {label && (
        <label htmlFor="search" className="block text-sm font-medium leading-6 text-gray-900">
          {label}
        </label>
      )}
      <div className="mt-2 space-x-1 py-1 pl-1.5 flex text-base items-center rounded ring-1 text-gray-900 ring-inset ring-gray-200 placeholder:text-gray-400">
        <input
          ref={inputRef}
          type="text"
          autoComplete="off"
          name="search"
          id="search"
          placeholder={placeHolder}
          onKeyDown={handleKeyPress}
          className="overflow-ellipsis w-full !border-0 !p-0 focus:!ring-0 !ml-1"
        />
        <div onClick={handleSearchClick} className="inset-y-0 right-0 flex py-1.5 pr-1.5 hover:cursor-pointer">
          <kbd className="inline-flex items-center rounded border border-gray-200 px-1 py-0.5 font-sans text-sm text-gray-400">
            Enter
          </kbd>
        </div>
      </div>
    </div>
  )
}
