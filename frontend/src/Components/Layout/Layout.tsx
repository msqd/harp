import { Link, Outlet, useLocation } from "react-router-dom"
import { Navbar } from "mkui/Components/Navbar"
import logo from "Assets/logo.svg"
import tw, { styled } from "twin.macro"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

function Layout() {
  const location = useLocation()
  return (
    <>
      <Navbar
        logo={logo}
        items={[
          { label: "Dashboard", to: "/", exact: true },
          { label: "Transactions", to: "/transactions" },
        ]}
        currentPath={location.pathname}
        Link={Link}
        Wrapper={StyledContainerWithHorizontalConstraint}
      />
      <StyledContainerWithHorizontalConstraint>
        <Outlet />
      </StyledContainerWithHorizontalConstraint>
    </>
  )
}

export default Layout
