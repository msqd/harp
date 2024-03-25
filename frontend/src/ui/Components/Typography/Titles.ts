import tw, { styled } from "twin.macro"

export const H1 = styled.h1(() => [tw`pb-6 text-2xl font-semibold text-gray-900`])
export const H2 = styled.h2(() => [tw`pb-4 text-xl font-semibold text-gray-900`])
export const H3 = styled.h3(() => [tw`pb-4 text-lg font-semibold text-gray-900`])
export const H4 = styled.h4(() => [tw`pb-4 text-base font-semibold text-gray-900`])
export const H5 = styled.h5(({ padding = undefined }: { padding?: string }) => [
  padding === undefined ? tw`pb-4` : padding,
  tw`text-sm font-semibold text-gray-900`,
])
export const H6 = styled.h6(() => [tw`pb-4 text-xs font-semibold text-gray-900`])
