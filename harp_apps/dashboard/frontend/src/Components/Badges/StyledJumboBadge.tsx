import tw, { styled } from "twin.macro"

export interface StyledJumboBadgeProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl"
  color?: "black" | "white"
}

export const StyledJumboBadge = styled.span(({ size = "sm", color = "white" }: StyledJumboBadgeProps) => [
  tw`rounded`,
  tw`select-none`,
  tw`px-2 py-0.5 font-semibold`,
  color === "black" ? tw`text-black` : "",
  color === "white" ? tw`text-white` : "",

  size === "xs" ? tw`text-xs px-1 py-0.5` : "",
  size === "sm" ? tw`text-sm px-1.5 py-0.5` : "",
  size === "md" ? tw`text-base` : "",
  size === "lg" ? tw`text-lg` : "",
  size === "lg" ? tw`md:(text-xl)` : "",
  size === "lg" ? tw`lg:(text-2xl)` : "",
  // extra large
  size === "xl" ? tw`text-2xl` : "",
  size === "xl" ? tw`md:(text-3xl)` : "",
  size === "xl" ? tw`lg:(text-4xl px-2 py-1)` : "",
])
