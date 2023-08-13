import tw, { styled } from "twin.macro";

const Styled = styled.div(() => [tw`text-blue-500`]);
function DashboardRoute() {
  return <Styled>Dashboard</Styled>;
}

export { DashboardRoute };
