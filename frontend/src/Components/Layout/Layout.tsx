import { Link, Outlet, useLocation } from "react-router-dom"
import { Navbar } from "mkui/Components/Navbar"
import logo from "Assets/logo.svg"
import tw, { styled } from "twin.macro"
import { useSystemQuery } from "Domain/System"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <div className="text-sm text-white" title={systemQuery.data.revision}>
      {`v.${systemQuery.data.version}`}
    </div>
  ) : null
}

function Layout() {
  const location = useLocation()
  return (
    <>
      <Navbar
        logo={logo}
        items={[
          { label: "Dashboard", to: "/", exact: true },
          { label: "Transactions", to: "/transactions" },
          { label: "Settings", to: "/settings" },
        ]}
        currentPath={location.pathname}
        Link={Link}
        Wrapper={StyledContainerWithHorizontalConstraint}
        rightChildren={<RightNav />}
      />
      <StyledContainerWithHorizontalConstraint>
        <Outlet />
      </StyledContainerWithHorizontalConstraint>
    </>
  )
}

export default Layout
