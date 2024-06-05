import { QuestionMarkCircleIcon, TagIcon, UserCircleIcon } from "@heroicons/react/20/solid"
import { Link, Outlet, useLocation } from "react-router-dom"
import tw, { styled } from "twin.macro"

import logo from "Assets/logo.svg"
import { useSystemQuery } from "Domain/System"
import { Navbar } from "ui/Components/Navbar"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

const navigationItems = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system" },
]

function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <div className="text-sm text-white text-right" title={systemQuery.data.revision}>
      <UserCircleIcon className="inline-block w-4 h-4 mr-1" />
      {systemQuery.data.user ?? "anonymous"}
      <br />
      <span className="text-xs">
        <a href="https://harp-proxy.rtfd.io/en/0.5/user/?utm_source=dashboard&utm_medium=help" target="_blank">
          <QuestionMarkCircleIcon className="inline-block w-4 h-4 mx-1" />
          Help
        </a>
        <TagIcon className="inline-block w-4 h-4 mx-1" />
        {`v.${systemQuery.data.version}`}
      </span>
    </div>
  ) : null
}

function Layout() {
  const location = useLocation()
  return (
    <div className="flex h-screen min-h-screen max-h-screen w-screen flex-col">
      <Navbar
        leftChildren={
          <Link to="/" className="flex">
            <img className="h-8 w-auto" src={logo} alt="Harp" />
            <span className="h-8 px-2 pt-1 text-md font-medium text-white" title="Harp Early Access">
              Harp EA
            </span>
          </Link>
        }
        items={navigationItems}
        currentPath={location.pathname}
        Link={Link}
        Wrapper={StyledContainerWithHorizontalConstraint}
        rightChildren={<RightNav />}
      />
      <StyledContainerWithHorizontalConstraint className="overflow-y-auto w-full">
        <Outlet />
      </StyledContainerWithHorizontalConstraint>
    </div>
  )
}

export default Layout
