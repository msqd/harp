import { Suspense } from "react"
import { Link, Outlet, useLocation } from "react-router-dom"
import tw, { styled } from "twin.macro"

import logo from "Assets/logo.svg"
import { Navbar } from "ui/Components/Navbar"

import { RightNav } from "./RightNav.tsx"

import { Loader } from "../Loader"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])
export interface NavigationItem {
  label: string
  to: string
  exact?: boolean
}

function Layout({
  title,
  navigationItems,
  navBarClassName,
}: {
  title: string
  navigationItems: NavigationItem[]
  navBarClassName?: string
}) {
  const location = useLocation()
  return (
    <div className="flex h-screen min-h-screen max-h-screen w-screen flex-col">
      <Navbar
        leftChildren={
          <Link to="/" className="flex">
            <img className="h-8 w-auto" src={logo} alt="HARP" />
            <span className="h-8 px-2 pt-1 text-md font-medium text-white" title={title}>
              {title}
            </span>
          </Link>
        }
        items={navigationItems}
        currentPath={location.pathname}
        Link={Link}
        Wrapper={StyledContainerWithHorizontalConstraint}
        rightChildren={<RightNav />}
        className={navBarClassName}
      />
      <StyledContainerWithHorizontalConstraint className="overflow-y-auto w-full">
        <Suspense fallback={<Loader className="my-20" />}>
          <Outlet />
        </Suspense>
      </StyledContainerWithHorizontalConstraint>
    </div>
  )
}

export default Layout
