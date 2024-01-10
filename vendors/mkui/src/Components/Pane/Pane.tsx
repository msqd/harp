import tw, { styled } from "twin.macro"

export const Pane = styled.div(
  ({ usePadding = true, className = undefined }: { usePadding?: boolean; className?: string }) => [
    tw`mb-4`,
    usePadding ? tw`px-4 py-3` : null,
    tw`max-w-full w-full`,
    tw`bg-white`,
    tw`shadow-sm ring-1 ring-black ring-opacity-5`,
    className ? `${className}` : null,
  ],
)
