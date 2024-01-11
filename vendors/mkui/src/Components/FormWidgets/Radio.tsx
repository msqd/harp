import { ReactNode } from "react"

export function Radio({
  name,
  label,
  inputProps = {},
  containerProps = {},
}: {
  name: string
  label?: string | ReactNode
  inputProps?: React.HTMLAttributes<HTMLInputElement>
  containerProps?: React.HTMLAttributes<HTMLDivElement>
}) {
  return (
    <div className="flex items-center gap-x-3 " {...containerProps}>
      <input
        id="push-everything"
        name="push-notifications"
        type="radio"
        className="h-4 w-4 border-gray-300 text-indigo-600 focus:ring-indigo-600"
        {...inputProps}
      />
      <label htmlFor="push-everything" className="block text-sm font-medium leading-6 text-gray-900">
        {label ?? name}
      </label>
    </div>
  )
}
