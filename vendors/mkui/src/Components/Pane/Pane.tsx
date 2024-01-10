import tw, { styled } from "twin.macro"

export const Pane = styled.div(() => [
  tw`px-4 py-3 mb-4`,
  tw`max-w-full w-full`,
  tw`bg-white`,
  tw`shadow-sm ring-1 ring-black ring-opacity-5`,
])
