import tw, { styled } from "twin.macro"

export type BadgeColor = "default" | "green" | "yellow" | "orange" | "red" | "blue" | "purple"

interface BadgeProps {
  color?: BadgeColor
}

export const Badge = styled.span(({ color = "default" }: BadgeProps) => [
  tw`inline-flex items-center`,
  tw`px-2 py-1`,
  tw`font-medium text-xs`,
  tw`rounded-md ring-1 ring-inset`,
  color == "default" && tw`bg-gray-50 text-gray-700 ring-gray-600/20`,
  color == "green" && tw`bg-green-50 text-green-700 ring-green-600/20`,
  color == "yellow" && tw`bg-yellow-50 text-yellow-700 ring-yellow-600/20`,
  color == "orange" && tw`bg-orange-50 text-orange-700 ring-orange-600/20`,
  color == "red" && tw`bg-red-50 text-red-700 ring-red-600/20`,
  color == "blue" && tw`bg-blue-50 text-blue-700 ring-blue-600/20`,
  color == "purple" && tw`bg-purple-50 text-purple-700 ring-purple-600/20`,
])
