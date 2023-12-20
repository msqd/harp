import { Link, Outlet, useLocation } from "react-router-dom"
import { Navbar } from "mkui/Components/Navbar"
import logo from "Assets/logo.svg"
import tw, { styled } from "twin.macro"
import { useSystemQuery } from "Domain/System"
import { TagIcon, UserCircleIcon } from "@heroicons/react/20/solid"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <div className="text-sm text-white text-right" title={systemQuery.data.revision}>
      <UserCircleIcon className="inline-block w-4 h-4 mr-1" />
      {systemQuery.data.user ?? "anonymous"}
      <br />

      <span className="text-xs">
        <TagIcon className="inline-block w-4 h-4 mr-1" />
        {`v.${systemQuery.data.version}`}
      </span>
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
