import tw, { styled } from "twin.macro"

const Styled = styled.div(() => [tw`text-blue-500`])
function DashboardRoute() {
  return <Styled>Here will lie the dashboard.</Styled>
}

export { DashboardRoute }
