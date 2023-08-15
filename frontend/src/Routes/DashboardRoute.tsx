import tw, { styled } from "twin.macro";
import { Button } from "mkui/Components/Button";

const Styled = styled.div(() => [tw`text-blue-500`]);
function DashboardRoute() {
  return (
    <Styled>
      Dashboard <Button>Hello</Button>
    </Styled>
  );
}

export { DashboardRoute };
