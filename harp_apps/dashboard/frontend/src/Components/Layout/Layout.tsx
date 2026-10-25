import { Suspense } from "react"
import { Link, Outlet, useLocation } from "react-router"
import tw, { styled } from "twin.macro"

import logo from "Assets/logo.svg"
import { Role, roleIncludes, useRole } from "Domain/System"
import { getDocumentationUrl } from "Utils/Documentation"
import { DevelopmentOnlyWarning } from "ui/Components/DevelopmentOnlyWarning"
import { Navbar } from "ui/Components/Navbar"

import { RightNav } from "./RightNav.tsx"

import { useSystemQuery } from "../../Domain/System"
import { Loader } from "../Loader"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

export interface NavigationItem {
  label: string
  to: string
  exact?: boolean
  /** The lowest role that may use the page; everyone, when unset. */
  requires?: Role
}

interface LayoutProps {
  title?: string
  navigationItems: NavigationItem[]
  navBarClassName?: string
}

function Layout({ title, navigationItems, navBarClassName }: LayoutProps) {
  const location = useLocation()
  const system = useSystemQuery().data
  const role = useRole()
  return (
    <div className="flex h-screen min-h-screen max-h-screen w-screen flex-col">
      <Navbar
        leftChildren={
          <Link to="/" className="flex">
            <img className="h-8 w-auto" src={logo} alt="HARP" />
            {title ? (
              <span className="h-8 px-2 pt-1 text-md font-medium text-white" title={title}>
                {title}
              </span>
            ) : null}
          </Link>
        }
        compactChildren={
          // Below `md` the right side lives in the hamburger menu: the pill must stay in the header bar.
          <DevelopmentOnlyWarning
            settings={system?.development_only_settings ?? []}
            documentationUrl={getDocumentationUrl(system?.version)}
          />
        }
        items={navigationItems.filter(({ requires }) => roleIncludes(role, requires ?? "viewer"))}
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
