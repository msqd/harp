import tw, {styled} from "twin.macro"

export const Pane = styled.div(({hasDefaultPadding = true, hasDefaultBorder = true,}: {
    hasDefaultPadding?: boolean,
    hasDefaultBorder?: boolean,
}) => [
    hasDefaultPadding && tw`px-4 py-3`,
    tw`max-w-full w-full`,
    tw`bg-white`,
    hasDefaultBorder && tw`shadow-sm ring-1 ring-black ring-opacity-5`,
])
