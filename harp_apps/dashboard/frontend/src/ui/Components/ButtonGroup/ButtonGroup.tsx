import tw, { styled } from "twin.macro"

interface ButtonProp {
  key: string
  title: string
}

type ButtonProps = Array<ButtonProp>

const StyledButton = styled.button(({ isCurrent = false }: { isCurrent: boolean }) => [
  tw`relative`,
  tw`-ml-px`,
  tw`px-3 py-2`,
  tw`inline-flex items-center`,
  tw`ring-1 ring-inset ring-gray-300`,
  tw`text-sm font-semibold`,
  isCurrent
    ? tw`text-white bg-primary-600 focus-visible:outline-blue-500`
    : tw`bg-white text-gray-900 hover:bg-gray-50`,
  tw`focus:z-10`,
])

export function ButtonGroup({
  buttonProps,
  current,
  setCurrent,
}: {
  buttonProps: ButtonProps
  current: string
  setCurrent: (current: string) => void
}) {
  return (
    <span className="isolate inline-flex rounded-md shadow-sm">
      {buttonProps.map((buttonProp) => {
        const { key, title } = buttonProp
        const isCurrent = key === current
        return (
          <StyledButton
            onClick={() => {
              setCurrent(key)
            }}
            key={key}
            type="button"
            isCurrent={isCurrent}
          >
            {title}
          </StyledButton>
        )
      })}
    </span>
  )
}
