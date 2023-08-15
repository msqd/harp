import { StyledComponent } from "@emotion/styled"
import { ReactNode } from "react"
import tw, { styled } from "twin.macro"

type ButtonVariant = "primary" | "secondary"

interface ButtonProps {
  children?: ReactNode
  variant?: ButtonVariant
}

const StyledComponents: Record<ButtonVariant, StyledComponent<JSX.IntrinsicElements["button"]>> = {
  primary: styled.button(() => [
    tw`px-2.5 py-1.5`,
    tw`mx-1`, // dubious ?
    tw`text-sm font-semibold`,
    tw`text-white bg-blue-600 hover:bg-blue-500 focus-visible:outline-blue-500`,
    tw`focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2`,
    tw`ring-1 ring-inset ring-blue-700 `,
  ]),
  secondary: styled.button(() => [
    tw`px-2.5 py-1.5`,
    tw`mx-1`, // dubious ?
    tw`text-sm font-semibold`,
    tw`bg-white text-gray-900 hover:bg-gray-50`,
    tw`ring-1 ring-inset ring-gray-300 `,
  ]),
}

const Button = ({ children, variant = "primary" }: ButtonProps) => {
  const Wrapper = StyledComponents[variant]
  return <Wrapper>{children}</Wrapper>
}

export { Button }
