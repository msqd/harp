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
      <div className="relative mt-2 flex items-center">
        <input
          ref={inputRef}
          type="text"
          name="search"
          id="search"
          placeholder={placeHolder}
          onKeyDown={handleKeyPress}
          className="block w-full rounded-md border-0 py-1.5 pr-14 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-8 focus:ring-inset focus:!ring-primary-300 sm:text-sm sm:leading-6"
        />
        <div onClick={handleSearchClick} className="absolute inset-y-0 right-0 flex py-1.5 pr-1.5 hover:cursor-pointer">
          <kbd className="inline-flex items-center rounded border border-gray-200 px-1 font-sans text-xs text-gray-400">
            Enter
          </kbd>
        </div>
      </div>
    </div>
  )
}
