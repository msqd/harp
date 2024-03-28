import { ReactNode, useRef } from "react"

import { classNames } from "../../Utilities"

export function Checkbox({
  name,
  label = undefined,
  checked = undefined,
  containerProps = {},
  labelProps = {},
  ...inputProps
}: {
  name: string
  label?: string | ReactNode
  checked?: boolean
  containerProps?: React.HTMLAttributes<HTMLDivElement>
  labelProps?: React.HTMLAttributes<HTMLLabelElement>
} & React.HTMLAttributes<HTMLInputElement>) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleContainerClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Prevent triggering the click event twice if the input itself is clicked
    const tagName = (e.target as Element).tagName
    if (tagName !== "INPUT" && inputRef.current) {
      inputRef.current.click()
      inputRef.current.focus()
    }
  }

  return (
    <div
      {...containerProps}
      className={classNames("relative flex gap-x-3 cursor-pointer select-none", containerProps.className)}
      onClick={handleContainerClick}
    >
      <div className="flex h-6 items-center">
        <input
          id={inputProps.id ?? name}
          name={name}
          ref={inputRef}
          type="checkbox"
          checked={checked}
          {...inputProps}
          className={classNames(
            "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 cursor-pointer",
            inputProps.className,
          )}
        />
      </div>
      <div className="text-sm leading-6">
        <label
          htmlFor={inputRef.current?.id ?? name}
          {...labelProps}
          className={classNames("font-medium text-gray-900 cursor-pointer", labelProps.className)}
          onClick={(e) => {
            // prevent default because the container's click handler will already handle this
            e.preventDefault()
          }}
        >
          {label ?? name}
        </label>
      </div>
    </div>
  )
}
